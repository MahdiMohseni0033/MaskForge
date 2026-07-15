import numpy as np
from PIL import Image

from medsam_prompt.visualization import mask_to_image, overlay_mask


def test_mask_and_overlay_are_png_ready() -> None:
    mask = np.array([[True, False], [False, False]])
    mask_image = mask_to_image(mask)
    overlay = overlay_mask(Image.new("RGB", (2, 2), color=(10, 20, 30)), mask, alpha=1.0)
    assert mask_image.getpixel((0, 0)) == 255
    assert overlay.getpixel((0, 0)) == (220, 38, 38)
