from PIL import Image

import medsam_prompt.streamlit_compat as streamlit_compat


def test_drawable_canvas_background_image_compatibility() -> None:
    image = Image.new("RGB", (8, 8))

    url = streamlit_compat.drawable_canvas.st_image.image_to_url(
        image,
        8,
        True,
        "RGB",
        "PNG",
        "test-canvas-background",
    )

    # Streamlit deliberately returns an empty URL when invoked without a runtime.
    assert url == ""
    assert callable(streamlit_compat.st_canvas)
