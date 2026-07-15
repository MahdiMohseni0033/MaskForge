from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .schemas import ClassInput


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-_").lower()
    return slug or "project"


PROJECT_SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    modified_at TEXT NOT NULL,
    last_image_id TEXT,
    overlay_opacity REAL NOT NULL DEFAULT 0.45,
    mask_visible INTEGER NOT NULL DEFAULT 1,
    schema_version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS classes (
    class_id INTEGER PRIMARY KEY CHECK (class_id BETWEEN 1 AND 65535),
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    color TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS images (
    image_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    stored_rel_path TEXT NOT NULL UNIQUE,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    source_format TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_started'
        CHECK(status IN ('not_started', 'in_progress', 'completed')),
    created_at TEXT NOT NULL,
    modified_at TEXT NOT NULL
);
"""


class ProjectRegistry:
    def __init__(self, workspace: Path):
        self.workspace = workspace.expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.workspace / "registry.sqlite"
        with self._registry_connection() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    root_path TEXT NOT NULL UNIQUE,
                    modified_at TEXT NOT NULL
                )"""
            )

    @contextmanager
    def _registry_connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.registry_path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    @contextmanager
    def connect(self, root: Path) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(root / "project.sqlite", timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def create_project(self, name: str, storage_path: str | None, classes: list[ClassInput]) -> str:
        project_id = str(uuid.uuid4())
        if storage_path:
            root = Path(storage_path).expanduser().resolve()
        else:
            root = self.workspace / "projects" / f"{slugify(name)}-{project_id[:8]}"
        database = root / "project.sqlite"
        if database.exists():
            raise FileExistsError("A labeling project already exists at that location")
        if root.exists() and any(root.iterdir()):
            raise FileExistsError("The selected project directory is not empty")
        root.mkdir(parents=True, exist_ok=True)
        (root / "images").mkdir()
        (root / "masks").mkdir()
        (root / "exports").mkdir()
        timestamp = now_iso()
        try:
            with self.connect(root) as connection:
                connection.executescript(PROJECT_SCHEMA)
                connection.execute(
                    "INSERT INTO project VALUES (?, ?, ?, ?, NULL, 0.45, 1, 1)",
                    (project_id, name, timestamp, timestamp),
                )
                next_id = 1
                for item in classes:
                    class_id = item.class_id
                    if class_id is None:
                        while any(c.class_id == next_id for c in classes):
                            next_id += 1
                        class_id = next_id
                        next_id += 1
                    connection.execute(
                        "INSERT INTO classes(class_id, name, color) VALUES (?, ?, ?)",
                        (class_id, item.name, item.color),
                    )
            self._register(project_id, name, root, timestamp)
        except Exception:
            if database.exists():
                database.unlink()
            raise
        return project_id

    def open_project(self, storage_path: str) -> str:
        root = Path(storage_path).expanduser().resolve()
        database = root / "project.sqlite"
        if not database.is_file():
            raise FileNotFoundError("No project.sqlite file was found in that directory")
        with self.connect(root) as connection:
            connection.executescript(PROJECT_SCHEMA)
            row = connection.execute("SELECT * FROM project").fetchone()
            if row is None:
                raise ValueError("The selected database is not a valid labeling project")
        self._register(row["project_id"], row["name"], root, row["modified_at"])
        return str(row["project_id"])

    def _register(self, project_id: str, name: str, root: Path, modified_at: str) -> None:
        with self._registry_connection() as connection:
            connection.execute(
                """INSERT INTO projects(project_id, name, root_path, modified_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(project_id) DO UPDATE SET
                     name=excluded.name, root_path=excluded.root_path,
                     modified_at=excluded.modified_at""",
                (project_id, name, str(root), modified_at),
            )

    def root_for(self, project_id: str) -> Path:
        with self._registry_connection() as connection:
            row = connection.execute(
                "SELECT root_path FROM projects WHERE project_id=?", (project_id,)
            ).fetchone()
        if row is None:
            raise KeyError("Project is not registered; reopen it by directory path")
        root = Path(row["root_path"]).resolve()
        if not (root / "project.sqlite").is_file():
            raise FileNotFoundError("Project directory is no longer available")
        return root

    def summaries(self) -> list[dict[str, Any]]:
        with self._registry_connection() as connection:
            rows = connection.execute("SELECT * FROM projects ORDER BY modified_at DESC").fetchall()
        return [
            {
                "project_id": row["project_id"],
                "name": row["name"],
                "storage_path": row["root_path"],
                "modified_at": row["modified_at"],
            }
            for row in rows
            if (Path(row["root_path"]) / "project.sqlite").is_file()
        ]

    def touch(self, project_id: str, connection: sqlite3.Connection) -> str:
        timestamp = now_iso()
        connection.execute(
            "UPDATE project SET modified_at=? WHERE project_id=?", (timestamp, project_id)
        )
        root = self.root_for(project_id)
        row = connection.execute("SELECT name FROM project").fetchone()
        self._register(project_id, row["name"], root, timestamp)
        return timestamp

    def detail(self, project_id: str) -> dict[str, Any]:
        root = self.root_for(project_id)
        with self.connect(root) as connection:
            project = connection.execute("SELECT * FROM project").fetchone()
            classes = connection.execute("SELECT * FROM classes ORDER BY class_id").fetchall()
            images = connection.execute(
                "SELECT * FROM images ORDER BY relative_path COLLATE NOCASE, image_id"
            ).fetchall()
        if project is None:
            raise ValueError("Invalid project database")
        return {
            "project_id": project["project_id"],
            "name": project["name"],
            "storage_path": str(root),
            "created_at": project["created_at"],
            "modified_at": project["modified_at"],
            "last_image_id": project["last_image_id"],
            "overlay_opacity": float(project["overlay_opacity"]),
            "mask_visible": bool(project["mask_visible"]),
            "classes": [dict(row) for row in classes],
            "images": [
                {
                    "image_id": row["image_id"],
                    "source_name": row["source_name"],
                    "relative_path": row["relative_path"],
                    "width": row["width"],
                    "height": row["height"],
                    "status": row["status"],
                    "modified_at": row["modified_at"],
                }
                for row in images
            ],
        }

    def dump_manifest(self, project_id: str) -> None:
        """Write a small human-readable pointer next to the SQLite database."""
        detail = self.detail(project_id)
        root = Path(detail["storage_path"])
        target = root / "project.json"
        temporary = root / ".project.json.tmp"
        temporary.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project_id": detail["project_id"],
                    "name": detail["name"],
                    "database": "project.sqlite",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
