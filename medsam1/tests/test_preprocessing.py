from PIL import Image
import numpy as np
import pytest

from medsam_prompt.preprocessing import ImageValidationError, ensure_rgb, image_to_medsam_input


def test_image_to_medsam_input_has_expected_shape_and_range() -> None:
    result = image_to_medsam_input(Image.new("RGB", (20, 10), color=(20, 40, 60)), size=16)
    assert result.shape == (16, 16, 3)
    assert result.dtype == np.float32
    assert np.all((0 <= result) & (result <= 1))


def test_ensure_rgb_rejects_degenerate_image() -> None:
    with pytest.raises(ImageValidationError):
        ensure_rgb(Image.new("RGB", (1, 3)))
