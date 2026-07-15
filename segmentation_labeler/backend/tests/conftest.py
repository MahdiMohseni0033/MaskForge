from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from seglabeler.api import create_app


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "registry"


@pytest.fixture
def client(workspace: Path) -> Iterator[TestClient]:
    value = TestClient(create_app(workspace=workspace, static_dir=workspace / "no-static"))
    yield value
    value.close()


@pytest.fixture
def project_payload(tmp_path: Path) -> dict[str, object]:
    return {
        "name": "Fixture project",
        "storage_path": str(tmp_path / "annotation-project"),
        "classes": [
            {"name": "Tissue", "color": "#EF4444"},
            {"name": "Instrument", "color": "#3B82F6"},
        ],
    }
