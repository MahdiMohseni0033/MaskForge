"""Streamlit UI for rectangle-prompted MedSAM 3 segmentation."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO

import streamlit as st
from PIL import Image

from medsam3_app import InferenceSettings, MedSAM3Paths, ModelConfigurationError, load_medsam3_model, run_inference
from medsam3_app.canvas_prompts import boxes_from_canvas
from medsam3_app.inference import BoxPrompt
from medsam3_app.preprocessing import ImageValidationError, ensure_rgb
from medsam3_app.streamlit_compat import st_canvas
from medsam3_app.visualization import make_overlay, mask_to_image


st.set_page_config(page_title="MedSAM 3 prompt segmentation", page_icon="🩹", layout="wide")
st.title("MedSAM 3 prompt segmentation")
st.caption("Draw one or more areas to guide official MedSAM 3 LoRA segmentation.")
st.warning("Technical research prototype only — not a clinically validated medical device.", icon="⚠️")


@st.cache_resource(show_spinner="Loading MedSAM 3 model and LoRA weights…")
def cached_model(paths: MedSAM3Paths, device: str, threshold: float):
    return load_medsam3_model(
        paths,
        device=device,  # type: ignore[arg-type]
        threshold=threshold,
        resolution=1008,
    )


def image_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def display_image(image: Image.Image, max_width: int = 700) -> tuple[Image.Image, float]:
    scale = min(1.0, max_width / image.width)
    displayed = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    return displayed, scale


with st.sidebar:
    st.header("Inference settings")
    device = st.selectbox("Device", ["auto", "cuda", "cpu"], help="Auto selects CUDA when available.")
    threshold = st.slider("Confidence threshold", 0.1, 1.0, 0.5, 0.05)
    st.divider()
    st.caption("The image is encoded once at the native 1008-pixel resolution and reused for every area.")

upload = st.file_uploader("Upload a de-identified image", type=["png", "jpg", "jpeg", "tif", "tiff"])
if upload is None:
    st.info("Upload an image, then draw one or more rectangular prompts.")
    st.stop()

try:
    image = ensure_rgb(Image.open(upload))
except (ImageValidationError, OSError) as error:
    st.error(f"The image could not be used: {error}")
    st.stop()

image_id = sha256(upload.getvalue()).hexdigest()[:12]
preview, scale = display_image(image)
box_prompts: list[BoxPrompt] = []

st.subheader("1. Create area prompts")
st.caption("Draw one or more rectangles. Every rectangle will be segmented and the masks will be merged.")
canvas = st_canvas(
    background_image=preview,
    drawing_mode="rect",
    fill_color="rgba(220, 38, 38, 0.18)",
    stroke_color="#dc2626",
    stroke_width=2,
    width=preview.width,
    height=preview.height,
    key=f"area-{image_id}",
)
if canvas.json_data and canvas.json_data.get("objects"):
    box_prompts = boxes_from_canvas(canvas.json_data["objects"], scale)
    if box_prompts:
        noun = "area" if len(box_prompts) == 1 else "areas"
        st.success(f"{len(box_prompts)} {noun} selected. All selected areas will be included.")

if not box_prompts:
    st.stop()

if st.button("2. Run MedSAM 3 segmentation", type="primary"):
    paths = MedSAM3Paths.from_environment()
    settings = InferenceSettings(threshold=threshold)
    try:
        model = cached_model(paths, device, threshold)
        with st.spinner(f"Encoding the image and decoding {len(box_prompts)} selected area(s)…"):
            result = run_inference(model, paths, image, box_prompts, settings)
    except (ModelConfigurationError, RuntimeError, ValueError) as error:
        st.error(str(error))
        st.stop()

    mask_image = mask_to_image(result.mask)
    overlay = make_overlay(image, result.mask)
    original, mask = st.columns(2)
    with original:
        st.image(image, caption="Original image", width="stretch")
    with mask:
        st.image(mask_image, caption="Predicted merged mask", width="stretch")
    st.image(overlay, caption="MedSAM 3 area-prompt overlay", width="stretch")
    message = f"Returned {result.instance_count} instance mask(s) from {len(box_prompts)} selected area(s)."
    if result.max_score is not None:
        message += f" Highest confidence: {result.max_score:.3f}."
    st.success(message)
    downloads = st.columns(2)
    with downloads[0]:
        st.download_button("Download mask PNG", image_png_bytes(mask_image), "medsam3_mask.png", "image/png")
    with downloads[1]:
        st.download_button("Download overlay PNG", image_png_bytes(overlay), "medsam3_overlay.png", "image/png")
