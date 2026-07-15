from __future__ import annotations

import gzip
import io
import json
import zipfile
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image
from seglabeler.api import create_app
from seglabeler.mask_ops import erase_stroke, fill_polygon, paint_stroke


def image_bytes(format_name: str, size: tuple[int, int] = (40, 32), value: int = 90) -> bytes:
    buffer = io.BytesIO()
    Image.new("L", size, value).save(buffer, format=format_name)
    return buffer.getvalue()


def create_project(client: TestClient, payload: dict[str, object]) -> dict[str, object]:
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_full_save_resume_navigation_and_export_workflow(
    client: TestClient,
    project_payload: dict[str, object],
    workspace: Path,
) -> None:
    project = create_project(client, project_payload)
    project_id = project["project_id"]
    upload = client.post(
        f"/api/projects/{project_id}/images/upload",
        files=[
            ("files", ("sample.jpg", image_bytes("JPEG"), "image/jpeg")),
            ("files", ("sample.tif", image_bytes("TIFF", value=120), "image/tiff")),
        ],
        data={"relative_paths": ["case/sample.jpg", "case/sample.tif"]},
    )
    assert upload.status_code == 200, upload.text
    result = upload.json()
    assert not result["errors"]
    assert len(result["imported"]) == 2

    first_id, second_id = [item["image_id"] for item in result["imported"]]
    mask = np.zeros((32, 40), dtype=np.uint16)
    mask = fill_polygon(mask, [(4, 4), (35, 4), (35, 25), (4, 25)], 1)
    mask = paint_stroke(mask, [(2, 29), (37, 29)], 5, 2)
    mask = erase_stroke(mask, [(20, 3), (20, 30)], 3)
    saved = client.put(
        f"/api/projects/{project_id}/images/{first_id}/mask",
        content=gzip.compress(mask.astype("<u2").tobytes()),
        headers={
            "Content-Type": "application/octet-stream",
            "Content-Encoding": "gzip",
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "in_progress"

    second_mask = np.zeros((32, 40), dtype=np.uint16)
    second_mask[10:20, 10:20] = 2
    assert (
        client.put(
            f"/api/projects/{project_id}/images/{second_id}/mask",
            content=second_mask.astype("<u2").tobytes(),
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/projects/{project_id}/images/{first_id}", json={"status": "completed"}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/projects/{project_id}",
            json={"last_image_id": second_id, "overlay_opacity": 0.6, "mask_visible": False},
        ).status_code
        == 200
    )

    restarted = TestClient(create_app(workspace=workspace, static_dir=workspace / "missing"))
    try:
        resumed = restarted.get(f"/api/projects/{project_id}").json()
        assert resumed["last_image_id"] == second_id
        assert resumed["overlay_opacity"] == 0.6
        assert resumed["mask_visible"] is False
        statuses = {item["image_id"]: item["status"] for item in resumed["images"]}
        assert statuses[first_id] == "completed"

        loaded = restarted.get(f"/api/projects/{project_id}/images/{first_id}/mask")
        assert loaded.headers["content-encoding"] == "gzip"
        restored_mask = np.frombuffer(loaded.content, dtype="<u2").reshape(32, 40)
        np.testing.assert_array_equal(restored_mask, mask)
        assert set(np.unique(restored_mask)) == {0, 1, 2}

        exported = restarted.post(
            f"/api/projects/{project_id}/export", json={"scope": "all", "format": "png"}
        )
        assert exported.status_code == 200, exported.text
        export_result = exported.json()
        names = {Path(item["mask"]).name for item in export_result["images"]}
        assert names == {"sample_jpg_mask.png", "sample_tif_mask.png"}
        metadata = json.loads(Path(export_result["metadata_file"]).read_text())
        assert metadata["background"]["class_id"] == 0
        assert [item["class_id"] for item in metadata["classes"]] == [1, 2]
        statistics = {item["class_id"]: item for item in metadata["class_statistics"]}
        assert statistics[1]["pixel_count"] > 0
        assert statistics[2]["images_present"] == 2
        summary = Path(export_result["summary_file"]).read_text()
        assert "ID\tLabel\tColor\tPixels\tImages containing class" in summary
        assert "1\tTissue\t#EF4444" in summary
        archive = restarted.get(export_result["download_url"])
        assert archive.status_code == 200
        with zipfile.ZipFile(io.BytesIO(archive.content)) as exported_zip:
            assert "classes.json" in exported_zip.namelist()
            assert "class_summary.txt" in exported_zip.namelist()
        for item in export_result["images"]:
            read_back = np.asarray(
                Image.open(Path(export_result["output_directory"]) / item["mask"])
            )
            assert read_back.shape == (32, 40)
            assert set(np.unique(read_back)).issubset({0, 1, 2})

        single = restarted.get(
            f"/api/projects/{project_id}/images/{first_id}/mask/download?format=png"
        )
        assert single.status_code == 200
        assert "sample_mask.png" in single.headers["content-disposition"]
        single_mask = np.asarray(Image.open(io.BytesIO(single.content)))
        np.testing.assert_array_equal(single_mask, mask.astype(np.uint8))
    finally:
        restarted.close()


def test_high_class_id_export_and_readback(client: TestClient, tmp_path: Path) -> None:
    project = create_project(
        client,
        {
            "name": "High IDs",
            "storage_path": str(tmp_path / "high-ids"),
            "classes": [{"class_id": 300, "name": "High", "color": "#ABCDEF"}],
        },
    )
    project_id = project["project_id"]
    upload = client.post(
        f"/api/projects/{project_id}/images/upload",
        files={"files": ("high.png", image_bytes("PNG", (12, 9)), "image/png")},
    ).json()
    image_id = upload["imported"][0]["image_id"]
    mask = np.zeros((9, 12), dtype=np.uint16)
    mask[2:6, 3:8] = 300
    assert (
        client.put(
            f"/api/projects/{project_id}/images/{image_id}/mask",
            content=mask.astype("<u2").tobytes(),
        ).status_code
        == 200
    )

    refused = client.post(
        f"/api/projects/{project_id}/export", json={"scope": "all", "format": "png"}
    )
    assert refused.status_code == 400
    assert "up to 255" in refused.json()["detail"]

    tiff_result = client.post(
        f"/api/projects/{project_id}/export", json={"scope": "all", "format": "tiff"}
    ).json()
    tiff_mask = np.asarray(
        Image.open(Path(tiff_result["output_directory"]) / tiff_result["images"][0]["mask"])
    )
    assert tiff_mask.dtype == np.uint16
    assert int(tiff_mask.max()) == 300

    npy_result = client.post(
        f"/api/projects/{project_id}/export", json={"scope": "all", "format": "npy"}
    ).json()
    npy_mask = np.load(
        Path(npy_result["output_directory"]) / npy_result["images"][0]["mask"],
        allow_pickle=False,
    )
    np.testing.assert_array_equal(npy_mask, mask)


def test_invalid_images_and_invalid_mask_are_reported(
    client: TestClient, project_payload: dict[str, object]
) -> None:
    project = create_project(client, project_payload)
    project_id = project["project_id"]
    upload = client.post(
        f"/api/projects/{project_id}/images/upload",
        files=[
            ("files", ("valid.png", image_bytes("PNG", (10, 8)), "image/png")),
            ("files", ("broken.png", b"not an image", "image/png")),
            ("files", ("notes.txt", b"hello", "text/plain")),
        ],
    )
    assert upload.status_code == 200
    result = upload.json()
    assert len(result["imported"]) == 1
    assert {item["file"] for item in result["errors"]} == {"broken.png", "notes.txt"}
    image_id = result["imported"][0]["image_id"]

    mismatched = io.BytesIO()
    Image.fromarray(np.zeros((4, 4), dtype=np.uint8)).save(mismatched, format="PNG")
    response = client.post(
        f"/api/projects/{project_id}/images/{image_id}/mask/import",
        files={"file": ("wrong.png", mismatched.getvalue(), "image/png")},
    )
    assert response.status_code == 400
    assert "do not match" in response.json()["detail"]

    unknown = io.BytesIO()
    Image.fromarray(np.full((8, 10), 9, dtype=np.uint8)).save(unknown, format="PNG")
    response = client.post(
        f"/api/projects/{project_id}/images/{image_id}/mask/import",
        files={"file": ("unknown.png", unknown.getvalue(), "image/png")},
    )
    assert response.status_code == 400
    assert "unknown class IDs" in response.json()["detail"]


def test_zip_and_local_directory_import_preserve_relative_paths(
    client: TestClient, project_payload: dict[str, object], tmp_path: Path
) -> None:
    project = create_project(client, project_payload)
    project_id = project["project_id"]
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("patient-a/slice.bmp", image_bytes("BMP", (7, 5)))
        archive.writestr("patient-b/slice.bmp", image_bytes("BMP", (7, 5), 130))
        archive.writestr("../escape.png", image_bytes("PNG", (7, 5)))
    archived = client.post(
        f"/api/projects/{project_id}/images/upload",
        files={"files": ("batch.zip", archive_bytes.getvalue(), "application/zip")},
    )
    assert archived.status_code == 200
    result = archived.json()
    assert {item["relative_path"] for item in result["imported"]} == {
        "patient-a/slice.bmp",
        "patient-b/slice.bmp",
    }
    assert result["errors"] == [{"file": "../escape.png", "error": "Unsafe relative path"}]

    local = tmp_path / "local-input"
    (local / "nested").mkdir(parents=True)
    (local / "root.png").write_bytes(image_bytes("PNG", (6, 4)))
    (local / "nested" / "child.webp").write_bytes(image_bytes("WEBP", (6, 4)))
    (local / "notes.txt").write_text("not an image", encoding="utf-8")
    directory_result = client.post(
        f"/api/projects/{project_id}/images/import-directory", json={"directory": str(local)}
    )
    assert directory_result.status_code == 200
    body = directory_result.json()
    assert {item["relative_path"] for item in body["imported"]} == {
        "root.png",
        "nested/child.webp",
    }
    assert body["errors"] == [{"file": "notes.txt", "error": "Unsupported file extension"}]
