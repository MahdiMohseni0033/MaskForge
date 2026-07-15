"""Portable rendering helpers for predicted masks."""

from __future__ import annotations

import numpy as np
from PIL import Image


def mask_to_image(mask: np.ndarray) -> Image.Image:
    _validate(mask)
    return Image.fromarray(mask.astype(np.uint8) * 255)


def overlay_mask(image: Image.Image, mask: np.ndarray, alpha: float = 0.45) -> Image.Image:
    _validate(mask)
    if not 0 <= alpha <= 1:
        raise ValueError("alpha must be between 0 and 1.")
    rgb = image.convert("RGB")
    if mask.shape != (rgb.height, rgb.width):
        raise ValueError("Mask dimensions must match the image dimensions.")
    pixels = np.asarray(rgb, dtype=np.float32).copy()
    pixels[mask] = pixels[mask] * (1 - alpha) + np.array([220, 38, 38]) * alpha
    return Image.fromarray(pixels.astype(np.uint8))


def _validate(mask: np.ndarray) -> None:
    if mask.ndim != 2:
        raise ValueError("Mask must be a two-dimensional array.")
