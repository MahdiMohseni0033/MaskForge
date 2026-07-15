"""Mask conversion and display helpers independent of Streamlit."""

from __future__ import annotations

import numpy as np
from PIL import Image


def mask_to_image(mask: np.ndarray) -> Image.Image:
    validated = _validate_mask(mask)
    return Image.fromarray(validated.astype(np.uint8) * 255)


def make_overlay(
    image: Image.Image,
    mask: np.ndarray,
    color: tuple[int, int, int] = (220, 38, 38),
    alpha: float = 0.45,
) -> Image.Image:
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be between 0 and 1.")
    validated = _validate_mask(mask)
    rgb = image.convert("RGB")
    if (rgb.height, rgb.width) != validated.shape:
        raise ValueError("Mask dimensions must match the image dimensions.")

    pixels = np.asarray(rgb, dtype=np.float32).copy()
    tint = np.asarray(color, dtype=np.float32)
    pixels[validated] = (1.0 - alpha) * pixels[validated] + alpha * tint
    return Image.fromarray(pixels.astype(np.uint8))


def _validate_mask(mask: np.ndarray) -> np.ndarray:
    if mask.ndim != 2:
        raise ValueError("Mask must be a two-dimensional array.")
    return mask.astype(bool, copy=False)
