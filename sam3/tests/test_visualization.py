import numpy as np
from PIL import Image
import pytest

from sam3_app.visualization import make_overlay, mask_to_image


def test_mask_to_image_is_binary_png_ready() -> None:
    result = mask_to_image(np.array([[False, True], [True, False]]))
    assert result.mode == "L"
    assert set(np.asarray(result).reshape(-1)) == {0, 255}


def test_overlay_changes_masked_pixels_only() -> None:
    image = Image.new("RGB", (2, 2), color=(10, 20, 30))
    mask = np.array([[True, False], [False, False]])
    result = make_overlay(image, mask, color=(210, 0, 0), alpha=1.0)
    assert result.getpixel((0, 0)) == (210, 0, 0)
    assert result.getpixel((1, 1)) == (10, 20, 30)


def test_overlay_rejects_size_mismatch() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        make_overlay(Image.new("RGB", (2, 2)), np.zeros((3, 2), dtype=bool))
