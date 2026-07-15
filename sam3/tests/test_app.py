from io import BytesIO
from pathlib import Path

from PIL import Image
from streamlit.testing.v1 import AppTest


def test_streamlit_app_reaches_upload_flow_without_errors() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=5)

    assert not app.exception
    assert app.title[0].value == "SAM 3 prompt segmentation"
    assert len(app.get("file_uploader")) == 1


def test_streamlit_upload_reaches_area_prompt_canvas_without_errors() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    buffer = BytesIO()
    Image.new("RGB", (64, 48), color=(120, 90, 70)).save(buffer, format="PNG")

    app = AppTest.from_file(str(app_path)).run(timeout=5)
    app.get("file_uploader")[0].upload(
        "deidentified-test.png", buffer.getvalue(), "image/png"
    ).run(timeout=10)

    assert not app.exception
    assert app.subheader[0].value == "1. Create area prompts"
