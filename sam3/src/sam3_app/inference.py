"""Native rectangle-prompted SAM 3 inference."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .models import LoadedSAM3, create_processor
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

    def xyxy(self, width: int, height: int) -> list[float]:
        self.validate(width, height)
        return [self.x0, self.y0, self.x1, self.y1]


@dataclass(frozen=True)
class InferenceResult:
    mask: np.ndarray
    instance_count: int
    mean_quality: float | None


def run_inference(
    loaded: LoadedSAM3,
    image: Image.Image,
    prompts: Sequence[BoxPrompt],
) -> InferenceResult:
    """Encode the image once, decode every box, and merge the returned masks."""
    prepared = ensure_rgb(image)
    if not prompts:
        raise ValueError("Draw at least one area before running segmentation.")
    boxes = np.asarray(
        [prompt.xyxy(prepared.width, prepared.height) for prompt in prompts],
        dtype=np.float32,
    )

    processor = create_processor(loaded)
    state = processor.set_image(prepared)
    masks, scores, _ = loaded.model.predict_inst(
        state,
        point_coords=None,
        point_labels=None,
        box=boxes,
        multimask_output=False,
    )
    mask_batch = _mask_batch(masks, prepared)
    score_values = np.asarray(scores, dtype=np.float32).reshape(-1)
    if len(mask_batch) != len(prompts):
        raise RuntimeError(
            f"SAM 3 returned {len(mask_batch)} masks for {len(prompts)} rectangle prompts."
        )
    combined = np.logical_or.reduce(mask_batch)
    return InferenceResult(
        mask=combined,
        instance_count=len(mask_batch),
        mean_quality=float(score_values.mean()) if score_values.size else None,
    )


def _mask_batch(value: object, image: Image.Image) -> np.ndarray:
    array = np.asarray(value).astype(bool)
    if array.ndim == 4 and array.shape[1] == 1:
        array = array[:, 0]
    if array.ndim == 2:
        array = array[None]
    if array.ndim != 3:
        raise RuntimeError(f"SAM 3 returned masks with unexpected shape {array.shape}.")
    if array.shape[1:] != (image.height, image.width):
        raise RuntimeError(
            f"SAM 3 returned mask dimensions {array.shape[1:]}; expected {(image.height, image.width)}."
        )
    return array
