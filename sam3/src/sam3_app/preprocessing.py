"""Input validation and lightweight image preparation."""

from __future__ import annotations

from PIL import Image


class ImageValidationError(ValueError):
    """Raised when an uploaded image is not suitable for inference."""


def ensure_rgb(image: Image.Image) -> Image.Image:
    """Return an RGB image and reject degenerate inputs early."""
    if image.width < 2 or image.height < 2:
        raise ImageValidationError("The image must be at least 2 × 2 pixels.")
    return image.convert("RGB")
