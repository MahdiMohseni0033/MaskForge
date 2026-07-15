from __future__ import annotations

import io
import tempfile
import uuid
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import numpy as np
import pydicom
from PIL import Image, UnidentifiedImageError

from .db import ProjectRegistry, now_iso

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
    ".npy",
    ".dcm",
}


@dataclass(frozen=True)
class Candidate:
    name: str
    relative_path: str
    content: bytes


def safe_relative_path(value: str) -> Path:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe relative path")
    parts = [part for part in path.parts if part not in ("", ".")]
    if not parts:
        raise ValueError("Filename is empty")
    return Path(*parts)


def _normalize_numeric(array: np.ndarray) -> Image.Image:
    if array.ndim != 2:
        raise ValueError("Only two-dimensional arrays are supported")
    if not np.issubdtype(array.dtype, np.number):
        raise ValueError("Array must contain numeric values")
    finite = np.isfinite(array)
    if not finite.any():
        raise ValueError("Array does not contain finite pixel values")
    values = array.astype(np.float64, copy=False)
    low = float(values[finite].min())
    high = float(values[finite].max())
    normalized = np.zeros(values.shape, dtype=np.uint8)
    if high > low:
        scaled = np.clip((values - low) / (high - low), 0, 1)
        normalized[finite] = np.round(scaled[finite] * 255).astype(np.uint8)
    return Image.fromarray(normalized)


def decode_image(candidate: Candidate) -> tuple[Image.Image, str]:
    suffix = Path(candidate.name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension '{suffix or '(none)'}'")
    try:
        if suffix == ".npy":
            array = np.load(io.BytesIO(candidate.content), allow_pickle=False)
            return _normalize_numeric(array), "NPY"
        if suffix == ".dcm":
            dataset = pydicom.dcmread(io.BytesIO(candidate.content))
            image = _normalize_numeric(np.asarray(dataset.pixel_array))
            if str(getattr(dataset, "PhotometricInterpretation", "")) == "MONOCHROME1":
                image = Image.fromarray(255 - np.asarray(image))
            return image, "DICOM"
        image = Image.open(io.BytesIO(candidate.content))
        image.load()
        if int(getattr(image, "n_frames", 1)) != 1:
            raise ValueError("Multi-page TIFF files are not supported; split pages before import")
        detected = str(image.format or "UNKNOWN").upper()
        allowed_formats = {"PNG", "JPEG", "TIFF", "BMP", "WEBP"}
        if detected not in allowed_formats:
            raise ValueError(f"Detected unsupported image content ({detected})")
        if image.mode not in {"L", "LA", "RGB", "RGBA"}:
            image = image.convert("RGB")
        return image, detected
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        if isinstance(exc, ValueError) and (
            "Multi-page" in str(exc) or "unsupported" in str(exc).lower()
        ):
            raise
        raise ValueError("File content is not a valid supported image") from exc
    except Exception as exc:
        if suffix in {".npy", ".dcm"}:
            raise ValueError(f"Could not decode {suffix[1:].upper()} image: {exc}") from exc
        raise


def expand_uploads(candidates: Iterable[Candidate]) -> tuple[list[Candidate], list[dict[str, str]]]:
    expanded: list[Candidate] = []
    errors: list[dict[str, str]] = []
    for candidate in candidates:
        if Path(candidate.name).suffix.lower() != ".zip":
            expanded.append(candidate)
            continue
        try:
            with zipfile.ZipFile(io.BytesIO(candidate.content)) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    try:
                        relative = safe_relative_path(info.filename)
                    except ValueError as exc:
                        errors.append({"file": info.filename, "error": str(exc)})
                        continue
                    expanded.append(
                        Candidate(relative.name, relative.as_posix(), archive.read(info))
                    )
        except (zipfile.BadZipFile, OSError) as exc:
            errors.append({"file": candidate.relative_path, "error": f"Invalid ZIP archive: {exc}"})
    return expanded, errors


def directory_candidates(directory: str) -> tuple[list[Candidate], list[dict[str, str]]]:
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError("The supplied local directory does not exist")
    candidates: list[Candidate] = []
    errors: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        resolved = path.resolve()
        if root not in resolved.parents:
            errors.append(
                {
                    "file": relative.as_posix(),
                    "error": "Symlink resolves outside selected directory",
                }
            )
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS and path.suffix.lower() != ".zip":
            errors.append({"file": relative.as_posix(), "error": "Unsupported file extension"})
            continue
        try:
            candidates.append(Candidate(path.name, relative.as_posix(), path.read_bytes()))
        except OSError as exc:
            errors.append({"file": relative.as_posix(), "error": f"Could not read file: {exc}"})
    return candidates, errors


def import_candidates(
    registry: ProjectRegistry, project_id: str, candidates: Iterable[Candidate]
) -> dict[str, object]:
    root = registry.root_for(project_id)
    imported: list[dict[str, object]] = []
    candidates, errors = expand_uploads(candidates)
    for candidate in candidates:
        try:
            relative = safe_relative_path(candidate.relative_path)
            image, source_format = decode_image(candidate)
            width, height = image.size
            if width < 1 or height < 1:
                raise ValueError("Image dimensions must be positive")
            image_id = str(uuid.uuid4())
            stored_rel = Path("images") / f"{image_id}.png"
            destination = root / stored_rel
            with tempfile.NamedTemporaryFile(
                dir=destination.parent, prefix=".image-", suffix=".png", delete=False
            ) as handle:
                temporary = Path(handle.name)
            try:
                image.save(temporary, format="PNG")
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
            mask = np.zeros((height, width), dtype=np.uint16)
            mask_destination = root / "masks" / f"{image_id}.npy"
            with tempfile.NamedTemporaryFile(
                dir=mask_destination.parent, prefix=".mask-", suffix=".npy", delete=False
            ) as handle:
                temporary_mask = Path(handle.name)
                np.save(handle, mask, allow_pickle=False)
            temporary_mask.replace(mask_destination)
            timestamp = now_iso()
            with registry.connect(root) as connection:
                connection.execute(
                    """INSERT INTO images(
                         image_id, source_name, relative_path, stored_rel_path, width, height,
                         source_format, status, created_at, modified_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, 'not_started', ?, ?)""",
                    (
                        image_id,
                        relative.name,
                        relative.as_posix(),
                        stored_rel.as_posix(),
                        width,
                        height,
                        source_format,
                        timestamp,
                        timestamp,
                    ),
                )
                registry.touch(project_id, connection)
            imported.append(
                {
                    "image_id": image_id,
                    "relative_path": relative.as_posix(),
                    "width": width,
                    "height": height,
                }
            )
        except Exception as exc:
            errors.append({"file": candidate.relative_path, "error": str(exc)})
    registry.dump_manifest(project_id)
    return {"imported": imported, "errors": errors}


def load_mask(root: Path, image_id: str) -> np.ndarray:
    path = root / "masks" / f"{image_id}.npy"
    try:
        mask = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise ValueError("Stored mask could not be read") from exc
    if mask.ndim != 2 or mask.dtype != np.uint16:
        raise ValueError("Stored mask has an invalid representation")
    return mask


def atomic_save_mask(path: Path, mask: np.ndarray) -> None:
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=".mask-", suffix=".npy", delete=False
    ) as handle:
        temporary = Path(handle.name)
        np.save(handle, mask.astype(np.uint16, copy=False), allow_pickle=False)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
