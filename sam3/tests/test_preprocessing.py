from PIL import Image
import pytest

from sam3_app.preprocessing import ImageValidationError, ensure_rgb


def test_ensure_rgb_converts_grayscale() -> None:
    result = ensure_rgb(Image.new("L", (4, 3), color=100))
    assert result.mode == "RGB"
    assert result.size == (4, 3)


def test_ensure_rgb_rejects_degenerate_image() -> None:
    with pytest.raises(ImageValidationError):
        ensure_rgb(Image.new("RGB", (1, 8)))
