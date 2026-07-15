"""Rectangle-prompted MedSAM 3 inference operations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from .models import MedSAM3Paths, create_box_processor, upstream_working_directory
from .preprocessing import ensure_rgb


@dataclass(frozen=True)
class BoxPrompt:
    x0: float
    y0: float
    x1: float
    y1: float

    def validate(self, width: int, height: int) -> None:
        if not (0 <= self.x0 < self.x1 <= width and 0 <= self.y0 < self.y1 <= height):
            raise ValueError("Draw a non-empty area fully inside the image.")

    def normalized_cxcywh(self, width: int, height: int) -> list[float]:
        self.validate(width, height)
        return [
            (self.x0 + self.x1) / (2 * width),
            (self.y0 + self.y1) / (2 * height),
            (self.x1 - self.x0) / width,
            (self.y1 - self.y0) / height,
        ]


@dataclass(frozen=True)
class InferenceSettings:
    threshold: float = 0.5
    resolution: int = 1008

    def validate(self) -> None:
        if not 0.0 < self.threshold <= 1.0:
            raise ValueError("Confidence threshold must be in (0, 1].")
        if self.resolution != 1008:
            raise ValueError("MedSAM 3 geometric prompts require the native 1008-pixel encoder resolution.")


@dataclass(frozen=True)
class InferenceResult:
    mask: np.ndarray
    instance_count: int
    max_score: float | None


def run_inference(
    model: Any,
    paths: MedSAM3Paths,
    image: Image.Image,
    prompts: Sequence[BoxPrompt],
    settings: InferenceSettings,
) -> InferenceResult:
    """Decode every positive rectangle and merge all returned instance masks."""
    settings.validate()
    prepared = ensure_rgb(image)
    if not prompts:
        raise ValueError("Draw at least one area before running segmentation.")
    for prompt in prompts:
        prompt.validate(prepared.width, prepared.height)

    with upstream_working_directory(paths):
        processor = create_box_processor(
            model,
            resolution=settings.resolution,
            threshold=settings.threshold,
        )
        state = processor.set_image(prepared)
        masks: list[np.ndarray] = []
        scores: list[float] = []
        for prompt in prompts:
            processor.reset_all_prompts(state)
            state = processor.add_geometric_prompt(
                prompt.normalized_cxcywh(prepared.width, prepared.height),
                True,
                state,
            )
            prompt_masks = _mask_batch(state.get("masks"), prepared)
            masks.extend(prompt_masks)
            scores.extend(_scores(state.get("scores")))

    combined = np.logical_or.reduce(masks) if masks else np.zeros((prepared.height, prepared.width), dtype=bool)
    return InferenceResult(
        mask=combined,
        instance_count=len(masks),
        max_score=max(scores) if scores else None,
    )


def _mask_batch(value: Any, image: Image.Image) -> list[np.ndarray]:
    if value is None:
        return []
    array = _as_numpy(value).astype(bool)
    if array.ndim == 4 and array.shape[1] == 1:
        array = array[:, 0]
    if array.ndim == 2:
        array = array[None]
    if array.ndim != 3:
        raise RuntimeError(f"MedSAM 3 returned masks with unexpected shape {array.shape}.")
    if array.shape[1:] != (image.height, image.width):
        raise RuntimeError(
            f"MedSAM 3 returned mask dimensions {array.shape[1:]}; expected {(image.height, image.width)}."
        )
    return [mask for mask in array]


def _scores(value: Any) -> list[float]:
    if value is None:
        return []
    return [float(score) for score in _as_numpy(value).reshape(-1)]


def _as_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    return np.asarray(value)
