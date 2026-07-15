from __future__ import annotations

import gzip
import io
import os
import sqlite3
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from . import __version__
from .db import ProjectRegistry, now_iso
from .exports import export_masks
from .importers import (
    Candidate,
    atomic_save_mask,
    directory_candidates,
    import_candidates,
    load_mask,
)
from .schemas import (
    ClassInput,
    ClassPatch,
    DirectoryImport,
    ExportRequest,
    ImageStatusPatch,
    ProjectCreate,
    ProjectOpen,
    ProjectSettings,
)


def _default_workspace() -> Path:
    configured = os.environ.get("SEGMENTATION_LABELER_WORKSPACE")
    return Path(configured).expanduser() if configured else Path.home() / ".segmentation_labeler"


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail=str(exc).strip("'"))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, FileExistsError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, sqlite3.IntegrityError):
        return HTTPException(status_code=409, detail="That class ID or name is already in use")
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail="The selected path is not writable")
    return HTTPException(status_code=400, detail=str(exc))


def _image_row(registry: ProjectRegistry, project_id: str, image_id: str):
    root = registry.root_for(project_id)
    with registry.connect(root) as connection:
        row = connection.execute("SELECT * FROM images WHERE image_id=?", (image_id,)).fetchone()
    if row is None:
        raise KeyError("Image was not found in this project")
    return root, row


def create_app(workspace: Path | None = None, static_dir: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="Segmentation Labeler API",
        version=__version__,
        description="Local persistence and export API for semantic segmentation masks.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registry = ProjectRegistry(workspace or _default_workspace())
    app.state.registry = registry

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/projects")
    def list_projects() -> list[dict[str, object]]:
        return registry.summaries()

    @app.post("/api/projects", status_code=201)
    def create_project(payload: ProjectCreate) -> dict[str, object]:
        try:
            project_id = registry.create_project(
                payload.name, payload.storage_path, payload.classes
            )
            registry.dump_manifest(project_id)
            return registry.detail(project_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.post("/api/projects/open")
    def open_project(payload: ProjectOpen) -> dict[str, object]:
        try:
            project_id = registry.open_project(payload.storage_path)
            return registry.detail(project_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> dict[str, object]:
        try:
            return registry.detail(project_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.patch("/api/projects/{project_id}")
    def update_project(project_id: str, payload: ProjectSettings) -> dict[str, object]:
        try:
            root = registry.root_for(project_id)
            fields: list[str] = []
            values: list[object] = []
            if payload.last_image_id is not None:
                with registry.connect(root) as check:
                    exists = check.execute(
                        "SELECT 1 FROM images WHERE image_id=?", (payload.last_image_id,)
                    ).fetchone()
                if exists is None:
                    raise ValueError("Last-opened image does not exist")
                fields.append("last_image_id=?")
                values.append(payload.last_image_id)
            if payload.overlay_opacity is not None:
                fields.append("overlay_opacity=?")
                values.append(payload.overlay_opacity)
            if payload.mask_visible is not None:
                fields.append("mask_visible=?")
                values.append(int(payload.mask_visible))
            if fields:
                with registry.connect(root) as connection:
                    values.append(project_id)
                    connection.execute(
                        f"UPDATE project SET {', '.join(fields)} WHERE project_id=?",  # noqa: S608
                        values,
                    )
                    registry.touch(project_id, connection)
            return registry.detail(project_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.post("/api/projects/{project_id}/classes", status_code=201)
    def add_class(project_id: str, payload: ClassInput) -> dict[str, object]:
        try:
            root = registry.root_for(project_id)
            with registry.connect(root) as connection:
                if payload.class_id is None:
                    maximum = connection.execute(
                        "SELECT COALESCE(MAX(class_id), 0) AS maximum FROM classes"
                    ).fetchone()["maximum"]
                    class_id = int(maximum) + 1
                else:
                    class_id = payload.class_id
                if class_id > 65535:
                    raise ValueError("No more class IDs are available")
                connection.execute(
                    "INSERT INTO classes(class_id, name, color) VALUES (?, ?, ?)",
                    (class_id, payload.name, payload.color),
                )
                registry.touch(project_id, connection)
            return {"class_id": class_id, "name": payload.name, "color": payload.color}
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.patch("/api/projects/{project_id}/classes/{class_id}")
    def update_class(project_id: str, class_id: int, payload: ClassPatch) -> dict[str, object]:
        try:
            root = registry.root_for(project_id)
            with registry.connect(root) as connection:
                current = connection.execute(
                    "SELECT * FROM classes WHERE class_id=?", (class_id,)
                ).fetchone()
                if current is None:
                    raise KeyError("Class was not found")
                name = payload.name if payload.name is not None else current["name"]
                color = payload.color if payload.color is not None else current["color"]
                connection.execute(
                    "UPDATE classes SET name=?, color=? WHERE class_id=?",
                    (name, color, class_id),
                )
                registry.touch(project_id, connection)
            return {"class_id": class_id, "name": name, "color": color}
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.delete("/api/projects/{project_id}/classes/{class_id}")
    def delete_class(
        project_id: str,
        class_id: int,
        replace_with_background: bool = Query(default=False),
    ) -> dict[str, object]:
        try:
            root = registry.root_for(project_id)
            with registry.connect(root) as connection:
                found = connection.execute(
                    "SELECT 1 FROM classes WHERE class_id=?", (class_id,)
                ).fetchone()
                if found is None:
                    raise KeyError("Class was not found")
                class_count = connection.execute(
                    "SELECT COUNT(*) AS count FROM classes"
                ).fetchone()["count"]
                if class_count <= 1:
                    raise ValueError("A project must retain at least one foreground class")
                images = connection.execute("SELECT image_id FROM images").fetchall()
            used = False
            for image in images:
                mask = load_mask(root, image["image_id"])
                if np.any(mask == class_id):
                    used = True
                    if replace_with_background:
                        mask[mask == class_id] = 0
                        atomic_save_mask(root / "masks" / f"{image['image_id']}.npy", mask)
            if used and not replace_with_background:
                raise ValueError(
                    "This class is used in masks; confirm replacement of its pixels with background"
                )
            with registry.connect(root) as connection:
                connection.execute("DELETE FROM classes WHERE class_id=?", (class_id,))
                registry.touch(project_id, connection)
            return {"deleted": class_id, "pixels_replaced_with": 0 if used else None}
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.post("/api/projects/{project_id}/images/upload")
    async def upload_images(
        project_id: str,
        files: list[UploadFile] = File(...),
        relative_paths: list[str] = Form(default=[]),
    ) -> dict[str, object]:
        try:
            registry.root_for(project_id)
            candidates = []
            for index, upload in enumerate(files):
                filename = upload.filename or f"upload-{index}"
                relative = relative_paths[index] if index < len(relative_paths) else filename
                candidates.append(Candidate(filename, relative, await upload.read()))
            return import_candidates(registry, project_id, candidates)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.post("/api/projects/{project_id}/images/import-directory")
    def import_directory(project_id: str, payload: DirectoryImport) -> dict[str, object]:
        try:
            candidates, errors = directory_candidates(payload.directory)
            result = import_candidates(registry, project_id, candidates)
            result["errors"] = errors + list(result["errors"])
            return result
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/projects/{project_id}/images/{image_id}/source")
    def source_image(project_id: str, image_id: str) -> FileResponse:
        try:
            root, row = _image_row(registry, project_id, image_id)
            path = (root / row["stored_rel_path"]).resolve()
            if root not in path.parents or not path.is_file():
                raise FileNotFoundError("Imported image file is missing")
            return FileResponse(
                path,
                media_type="image/png",
                filename=row["source_name"],
                headers={"Cache-Control": "private, max-age=3600"},
            )
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/projects/{project_id}/images/{image_id}/mask")
    def get_mask(project_id: str, image_id: str, request: Request) -> Response:
        try:
            root, row = _image_row(registry, project_id, image_id)
            mask = load_mask(root, image_id)
            if mask.shape != (row["height"], row["width"]):
                raise ValueError("Stored mask dimensions do not match the image")
            content = mask.astype("<u2", copy=False).tobytes()
            headers = {
                "X-Mask-Width": str(row["width"]),
                "X-Mask-Height": str(row["height"]),
                "X-Mask-Dtype": "uint16-le",
                "Cache-Control": "no-store",
            }
            if "gzip" in request.headers.get("accept-encoding", "").lower() and len(content) > 1024:
                content = gzip.compress(content, compresslevel=3)
                headers["Content-Encoding"] = "gzip"
            return Response(
                content=content,
                media_type="application/octet-stream",
                headers=headers,
            )
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.put("/api/projects/{project_id}/images/{image_id}/mask")
    async def save_mask(project_id: str, image_id: str, request: Request) -> dict[str, object]:
        try:
            root, row = _image_row(registry, project_id, image_id)
            content = await request.body()
            if request.headers.get("content-encoding", "").lower() == "gzip":
                try:
                    content = gzip.decompress(content)
                except (gzip.BadGzipFile, OSError) as exc:
                    raise ValueError("Mask payload is not valid gzip data") from exc
            expected = int(row["width"]) * int(row["height"]) * 2
            if len(content) != expected:
                raise ValueError(
                    f"Mask payload has {len(content)} bytes; expected {expected} for this image"
                )
            mask = np.frombuffer(content, dtype="<u2").reshape(row["height"], row["width"])
            with registry.connect(root) as connection:
                valid_ids = {
                    item["class_id"] for item in connection.execute("SELECT class_id FROM classes")
                }
                invalid = set(np.unique(mask).tolist()) - valid_ids - {0}
                if invalid:
                    raise ValueError(f"Mask contains unknown class IDs: {sorted(invalid)[:10]}")
                atomic_save_mask(root / "masks" / f"{image_id}.npy", mask)
                timestamp = now_iso()
                status = row["status"]
                if status != "completed":
                    status = "in_progress" if np.any(mask) else "not_started"
                connection.execute(
                    "UPDATE images SET status=?, modified_at=? WHERE image_id=?",
                    (status, timestamp, image_id),
                )
                registry.touch(project_id, connection)
            return {"saved": True, "modified_at": timestamp, "status": status}
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.post("/api/projects/{project_id}/images/{image_id}/mask/import")
    async def import_mask(
        project_id: str, image_id: str, file: UploadFile = File(...)
    ) -> dict[str, object]:
        try:
            root, row = _image_row(registry, project_id, image_id)
            content = await file.read()
            suffix = Path(file.filename or "").suffix.lower()
            if suffix == ".npy":
                candidate = np.load(io.BytesIO(content), allow_pickle=False)
            else:
                candidate = np.asarray(Image.open(io.BytesIO(content)))
            if candidate.ndim != 2:
                raise ValueError("Imported mask must be a two-dimensional indexed image")
            if candidate.shape != (row["height"], row["width"]):
                raise ValueError(
                    f"Mask dimensions {candidate.shape[1]}x{candidate.shape[0]} do not match "
                    f"image dimensions {row['width']}x{row['height']}"
                )
            if not np.issubdtype(candidate.dtype, np.integer):
                raise ValueError("Imported mask values must be integers")
            if candidate.min(initial=0) < 0 or candidate.max(initial=0) > 65535:
                raise ValueError("Imported mask values must be between 0 and 65535")
            mask = candidate.astype(np.uint16)
            with registry.connect(root) as connection:
                valid_ids = {
                    item["class_id"] for item in connection.execute("SELECT class_id FROM classes")
                }
                invalid = set(np.unique(mask).tolist()) - valid_ids - {0}
                if invalid:
                    raise ValueError(f"Mask contains unknown class IDs: {sorted(invalid)[:10]}")
                atomic_save_mask(root / "masks" / f"{image_id}.npy", mask)
                timestamp = now_iso()
                status = "in_progress" if np.any(mask) else "not_started"
                connection.execute(
                    "UPDATE images SET status=?, modified_at=? WHERE image_id=?",
                    (status, timestamp, image_id),
                )
                registry.touch(project_id, connection)
            return {"imported": True, "status": status}
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(
                status_code=400, detail="Imported mask is not a valid image"
            ) from exc
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.patch("/api/projects/{project_id}/images/{image_id}")
    def update_image_status(
        project_id: str, image_id: str, payload: ImageStatusPatch
    ) -> dict[str, object]:
        try:
            root, _ = _image_row(registry, project_id, image_id)
            timestamp = now_iso()
            with registry.connect(root) as connection:
                connection.execute(
                    "UPDATE images SET status=?, modified_at=? WHERE image_id=?",
                    (payload.status, timestamp, image_id),
                )
                registry.touch(project_id, connection)
            return {"image_id": image_id, "status": payload.status, "modified_at": timestamp}
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.post("/api/projects/{project_id}/export")
    def export(project_id: str, payload: ExportRequest) -> dict[str, object]:
        try:
            return export_masks(registry, project_id, payload)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/projects/{project_id}/images/{image_id}/mask/download")
    def download_current_mask(
        project_id: str,
        image_id: str,
        format: Literal["png", "tiff", "npy"] = Query(default="png"),
    ) -> Response:
        try:
            root, row = _image_row(registry, project_id, image_id)
            mask = load_mask(root, image_id)
            with registry.connect(root) as connection:
                maximum = connection.execute(
                    "SELECT COALESCE(MAX(class_id), 0) AS maximum FROM classes"
                ).fetchone()["maximum"]
            if format == "png" and maximum > 255:
                raise ValueError(
                    "Class-indexed PNG supports class IDs up to 255; choose TIFF or NumPy"
                )
            output = io.BytesIO()
            extension = {"png": ".png", "tiff": ".tif", "npy": ".npy"}[format]
            media_type = {
                "png": "image/png",
                "tiff": "image/tiff",
                "npy": "application/octet-stream",
            }[format]
            if format == "png":
                Image.fromarray(mask.astype(np.uint8)).save(output, format="PNG")
            elif format == "tiff":
                Image.fromarray(mask.astype(np.uint16)).save(output, format="TIFF")
            else:
                np.save(output, mask, allow_pickle=False)
            stem = Path(row["source_name"]).stem
            safe_stem = (
                "".join(
                    character if character.isalnum() or character in "-_" else "_"
                    for character in stem
                ).strip("_")
                or "image"
            )
            filename = f"{safe_stem}_mask{extension}"
            return Response(
                content=output.getvalue(),
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/projects/{project_id}/exports/{archive_name}")
    def download_export(project_id: str, archive_name: str) -> FileResponse:
        try:
            if Path(archive_name).name != archive_name or not archive_name.endswith(".zip"):
                raise ValueError("Invalid export archive name")
            root = registry.root_for(project_id)
            downloads = (root / "exports" / "downloads").resolve()
            archive = (downloads / archive_name).resolve()
            if archive.parent != downloads or not archive.is_file():
                raise FileNotFoundError("Export archive was not found")
            return FileResponse(
                archive,
                media_type="application/zip",
                filename=archive_name,
                headers={"Cache-Control": "no-store"},
            )
        except Exception as exc:
            raise _http_error(exc) from exc

    resolved_static = static_dir
    if resolved_static is None:
        resolved_static = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if resolved_static.is_dir():
        app.mount("/", StaticFiles(directory=resolved_static, html=True), name="frontend")

    return app


app = create_app()
