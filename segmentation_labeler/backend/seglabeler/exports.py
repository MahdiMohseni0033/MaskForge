from __future__ import annotations

import json
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from . import __version__
from .db import ProjectRegistry
from .importers import load_mask, safe_relative_path
from .schemas import ExportRequest


def _new_export_directory(base: Path, project_name: str) -> Path:
    base = base.expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in project_name).strip("-")
    candidate = base / f"{safe_name or 'project'}-export-{timestamp}"
    candidate.mkdir()
    return candidate


def _selected_rows(connection: Any, request: ExportRequest) -> list[Any]:
    if request.scope == "current":
        ids = [request.current_image_id] if request.current_image_id else []
    elif request.scope == "selected":
        ids = request.image_ids
    else:
        return connection.execute(
            "SELECT * FROM images ORDER BY relative_path COLLATE NOCASE, image_id"
        ).fetchall()
    if not ids:
        raise ValueError(f"No images were supplied for the '{request.scope}' export scope")
    placeholders = ",".join("?" for _ in ids)
    rows = connection.execute(
        f"SELECT * FROM images WHERE image_id IN ({placeholders})",
        ids,  # noqa: S608
    ).fetchall()
    if len(rows) != len(set(ids)):
        raise ValueError("One or more selected image IDs do not exist")
    by_id = {row["image_id"]: row for row in rows}
    return [by_id[image_id] for image_id in ids]


def _output_relative_paths(rows: list[Any], extension: str) -> dict[str, Path]:
    stem_counts = Counter()
    parsed: dict[str, Path] = {}
    for row in rows:
        source = safe_relative_path(row["relative_path"])
        parsed[row["image_id"]] = source
        stem_counts[(source.parent.as_posix(), source.stem.casefold())] += 1
    used: set[str] = set()
    result: dict[str, Path] = {}
    for row in rows:
        source = parsed[row["image_id"]]
        stem = source.stem
        if stem_counts[(source.parent.as_posix(), source.stem.casefold())] > 1:
            source_extension = source.suffix.lower().lstrip(".") or "file"
            stem = f"{stem}_{source_extension}"
        target = source.parent / f"{stem}_mask{extension}"
        if target.as_posix().casefold() in used:
            target = source.parent / f"{stem}_{row['image_id'][:8]}_mask{extension}"
        used.add(target.as_posix().casefold())
        result[row["image_id"]] = target
    return result


def export_masks(
    registry: ProjectRegistry, project_id: str, request: ExportRequest
) -> dict[str, object]:
    root = registry.root_for(project_id)
    with registry.connect(root) as connection:
        project = connection.execute("SELECT * FROM project").fetchone()
        classes = connection.execute("SELECT * FROM classes ORDER BY class_id").fetchall()
        rows = _selected_rows(connection, request)
    if not rows:
        raise ValueError("The project has no images to export")
    max_class_id = max((row["class_id"] for row in classes), default=0)
    if request.format == "png" and max_class_id > 255:
        raise ValueError(
            "Class-indexed PNG supports class IDs up to 255; choose 16-bit TIFF or NumPy"
        )
    base = (
        Path(request.export_directory).expanduser()
        if request.export_directory
        else root / "exports"
    )
    output = _new_export_directory(base, project["name"])
    extension = {"png": ".png", "tiff": ".tif", "npy": ".npy"}[request.format]
    targets = _output_relative_paths(rows, extension)
    mapping: list[dict[str, object]] = []
    all_class_ids = [0, *(row["class_id"] for row in classes)]
    total_pixels = {class_id: 0 for class_id in all_class_ids}
    images_present = {class_id: 0 for class_id in all_class_ids}
    for row in rows:
        mask = load_mask(root, row["image_id"])
        if mask.shape != (row["height"], row["width"]):
            raise ValueError(f"Stored mask dimensions are invalid for {row['relative_path']}")
        target_relative = targets[row["image_id"]]
        target = output / target_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.tmp")
        if request.format == "png":
            Image.fromarray(mask.astype(np.uint8)).save(temporary, format="PNG")
        elif request.format == "tiff":
            Image.fromarray(mask.astype(np.uint16)).save(temporary, format="TIFF")
        else:
            with temporary.open("wb") as handle:
                np.save(handle, mask, allow_pickle=False)
        temporary.replace(target)
        values, counts = np.unique(mask, return_counts=True)
        image_counts = {int(value): int(count) for value, count in zip(values, counts, strict=True)}
        for class_id in all_class_ids:
            count = image_counts.get(class_id, 0)
            total_pixels[class_id] += count
            if count:
                images_present[class_id] += 1
        mapping.append(
            {
                "image_id": row["image_id"],
                "source": row["relative_path"],
                "mask": target_relative.as_posix(),
                "width": row["width"],
                "height": row["height"],
                "class_pixel_counts": {
                    str(class_id): image_counts.get(class_id, 0) for class_id in all_class_ids
                },
            }
        )
    class_definitions = [
        {"class_id": 0, "name": "Background", "color": "#000000"},
        *(dict(row) for row in classes),
    ]
    statistics = [
        {
            **item,
            "pixel_count": total_pixels[item["class_id"]],
            "images_present": images_present[item["class_id"]],
        }
        for item in class_definitions
    ]
    metadata = {
        "schema_version": 1,
        "application": "segmentation-labeler",
        "application_version": __version__,
        "project_id": project_id,
        "project_name": project["name"],
        "export_format": request.format,
        "background": {"class_id": 0, "name": "Background", "color": "#000000"},
        "classes": [dict(row) for row in classes],
        "class_statistics": statistics,
        "images": mapping,
    }
    metadata_path = output / "classes.json"
    temporary_metadata = output / ".classes.json.tmp"
    temporary_metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    temporary_metadata.replace(metadata_path)

    summary_path = output / "class_summary.txt"
    summary_lines = [
        f"Project: {project['name']}",
        f"Project ID: {project_id}",
        f"Export format: {request.format}",
        f"Number of images: {len(rows)}",
        "",
        "Class summary",
        "ID\tLabel\tColor\tPixels\tImages containing class",
    ]
    summary_lines.extend(
        f"{item['class_id']}\t{item['name']}\t{item['color']}\t{item['pixel_count']}\t"
        f"{item['images_present']}"
        for item in statistics
    )
    summary_lines.extend(["", "Per-image pixel counts"])
    for item in mapping:
        summary_lines.append(f"{item['source']} ({item['width']}x{item['height']})")
        counts = item["class_pixel_counts"]
        for class_item in class_definitions:
            summary_lines.append(
                f"  ID {class_item['class_id']} {class_item['name']}: "
                f"{counts[str(class_item['class_id'])]} pixels"
            )
    temporary_summary = output / ".class_summary.txt.tmp"
    temporary_summary.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    temporary_summary.replace(summary_path)

    downloads = root / "exports" / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    archive_name = f"{output.name}.zip"
    archive_path = downloads / archive_name
    temporary_archive = downloads / f".{archive_name}.tmp"
    with zipfile.ZipFile(temporary_archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(output.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(output).as_posix())
    temporary_archive.replace(archive_path)
    return {
        "output_directory": str(output),
        "metadata_file": str(metadata_path),
        "summary_file": str(summary_path),
        "archive_name": archive_name,
        "download_url": f"/api/projects/{project_id}/exports/{archive_name}",
        "images": mapping,
    }
