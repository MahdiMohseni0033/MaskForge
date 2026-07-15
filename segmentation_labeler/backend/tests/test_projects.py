from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from seglabeler.api import create_app


def test_create_reopen_and_stable_class_ids(
    client: TestClient, project_payload: dict[str, object], workspace: Path
) -> None:
    response = client.post("/api/projects", json=project_payload)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["name"] == "Fixture project"
    assert [item["class_id"] for item in created["classes"]] == [1, 2]
    assert Path(created["storage_path"], "project.sqlite").is_file()
    assert Path(created["storage_path"], "project.json").is_file()

    project_id = created["project_id"]
    updated = client.patch(
        f"/api/projects/{project_id}/classes/1",
        json={"name": "Renamed tissue", "color": "#22C55E"},
    )
    assert updated.status_code == 200
    assert updated.json()["class_id"] == 1
    added = client.post(
        f"/api/projects/{project_id}/classes", json={"name": "Fluid", "color": "#A855F7"}
    )
    assert added.status_code == 201
    assert added.json()["class_id"] == 3

    # A new application instance can recover the same project through the persistent registry.
    restarted = TestClient(create_app(workspace=workspace, static_dir=workspace / "missing"))
    try:
        reopened = restarted.get(f"/api/projects/{project_id}")
        assert reopened.status_code == 200
        assert [item["class_id"] for item in reopened.json()["classes"]] == [1, 2, 3]
        explicit = restarted.post(
            "/api/projects/open", json={"storage_path": created["storage_path"]}
        )
        assert explicit.status_code == 200
        assert explicit.json()["project_id"] == project_id
    finally:
        restarted.close()


def test_class_validation(client: TestClient, tmp_path: Path) -> None:
    duplicate = client.post(
        "/api/projects",
        json={
            "name": "Bad classes",
            "storage_path": str(tmp_path / "bad"),
            "classes": [
                {"class_id": 1, "name": "Same", "color": "#000001"},
                {"class_id": 2, "name": "same", "color": "#000002"},
            ],
        },
    )
    assert duplicate.status_code == 422
    background = client.post(
        "/api/projects",
        json={
            "name": "Background misuse",
            "storage_path": str(tmp_path / "bad-background"),
            "classes": [{"class_id": 0, "name": "Bad", "color": "#FFFFFF"}],
        },
    )
    assert background.status_code == 422
