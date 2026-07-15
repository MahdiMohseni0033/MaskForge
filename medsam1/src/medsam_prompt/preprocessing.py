"""Image validation and deterministic MedSAM preprocessing."""

from __future__ import annotations

import numpy as np
from PIL import Image


class ImageValidationError(ValueError):
    """Raised when the uploaded image cannot be prepared for MedSAM."""


def ensure_rgb(image: Image.Image) -> Image.Image:
    if image.width < 2 or image.height < 2:
        raise ImageValidationError("The image must be at least 2 × 2 pixels.")
    return image.convert("RGB")


def image_to_medsam_input(image: Image.Image, size: int = 1024) -> np.ndarray:
    """Resize and normalise RGB input exactly once before the image encoder."""
    rgb = ensure_rgb(image)
    resized = np.asarray(rgb.resize((size, size), Image.Resampling.BICUBIC), dtype=np.float32)
    minimum, maximum = float(resized.min()), float(resized.max())
    return (resized - minimum) / max(maximum - minimum, 1e-8)
