from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ClassInput(BaseModel):
    class_id: int | None = Field(default=None, ge=1, le=65535)
    name: str = Field(min_length=1, max_length=100)
    color: str

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Class name cannot be blank")
        return value

    @field_validator("color")
    @classmethod
    def valid_color(cls, value: str) -> str:
        value = value.upper()
        if len(value) != 7 or value[0] != "#":
            raise ValueError("Color must use #RRGGBB format")
        try:
            int(value[1:], 16)
        except ValueError as exc:
            raise ValueError("Color must use #RRGGBB format") from exc
        return value


class ClassOut(BaseModel):
    class_id: int
    name: str
    color: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    storage_path: str | None = None
    classes: list[ClassInput] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def clean_project_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project name cannot be blank")
        return value

    @model_validator(mode="after")
    def unique_classes(self) -> ProjectCreate:
        ids = [item.class_id for item in self.classes if item.class_id is not None]
        names = [item.name.casefold() for item in self.classes]
        if len(ids) != len(set(ids)):
            raise ValueError("Class IDs must be unique")
        if len(names) != len(set(names)):
            raise ValueError("Class names must be unique")
        return self


class ProjectOpen(BaseModel):
    storage_path: str = Field(min_length=1)


class ImageOut(BaseModel):
    image_id: str
    source_name: str
    relative_path: str
    width: int
    height: int
    status: Literal["not_started", "in_progress", "completed"]
    modified_at: str


class ProjectOut(BaseModel):
    project_id: str
    name: str
    storage_path: str
    created_at: str
    modified_at: str
    last_image_id: str | None
    overlay_opacity: float
    mask_visible: bool
    classes: list[ClassOut]
    images: list[ImageOut]


class ProjectSummary(BaseModel):
    project_id: str
    name: str
    storage_path: str
    modified_at: str


class ProjectSettings(BaseModel):
    last_image_id: str | None = None
    overlay_opacity: float | None = Field(default=None, ge=0, le=1)
    mask_visible: bool | None = None


class ClassPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Class name cannot be blank")
        return value

    @field_validator("color")
    @classmethod
    def valid_color(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return ClassInput.valid_color(value)


class DirectoryImport(BaseModel):
    directory: str = Field(min_length=1)


class ImageStatusPatch(BaseModel):
    status: Literal["not_started", "in_progress", "completed"]


class ExportRequest(BaseModel):
    scope: Literal["current", "selected", "all"] = "all"
    image_ids: list[str] = []
    current_image_id: str | None = None
    format: Literal["png", "tiff", "npy"] = "png"
    export_directory: str | None = None
