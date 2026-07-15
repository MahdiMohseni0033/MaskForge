"""Streamlit UI for point- and area-prompted MedSAM segmentation."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO

import streamlit as st
from PIL import Image

from medsam_prompt.canvas_prompts import boxes_from_canvas, last_point_from_canvas
from medsam_prompt.inference import (
    BoxPrompt,
    PointPrompt,
    encode_image,
    segment_from_box_prompts,
    segment_from_prompt,
)
from medsam_prompt.model import MedSAMPaths, ModelConfigurationError, load_medsam
from medsam_prompt.preprocessing import ImageValidationError, ensure_rgb
from medsam_prompt.streamlit_compat import st_canvas
from medsam_prompt.visualization import mask_to_image, overlay_mask


st.set_page_config(page_title="MedSAM prompt segmentation", page_icon="🩺", layout="wide")
st.title("MedSAM prompt segmentation")
st.caption("Draw an area or click a point to guide official MedSAM segmentation.")
st.warning("Technical research prototype only — not a clinically validated medical device.", icon="⚠️")


@st.cache_resource(show_spinner="Loading MedSAM checkpoint…")
def cached_model(paths: MedSAMPaths, device: str):
    return load_medsam(paths, device)


def image_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def display_image(image: Image.Image, max_width: int = 700) -> tuple[Image.Image, float]:
    scale = min(1.0, max_width / image.width)
    displayed = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    return displayed, scale


with st.sidebar:
    st.header("Prompt and device")
    prompt_mode = st.radio("Prompt", ["Area (recommended)", "Point"], help="MedSAM was fine-tuned with box prompts.")
    device = st.selectbox("Device", ["auto", "cuda", "cpu"], help="Auto selects CUDA when PyTorch can access the GPU.")
    st.divider()
    st.caption("The image embedding is computed once per run and reused for every selected area.")

upload = st.file_uploader("Upload a de-identified image", type=["png", "jpg", "jpeg", "tif", "tiff"])
if upload is None:
    st.info("Upload an image, then create one area or point prompt.")
    st.stop()

try:
    image = ensure_rgb(Image.open(upload))
except (ImageValidationError, OSError) as error:
    st.error(f"The image could not be used: {error}")
    st.stop()

image_id = sha256(upload.getvalue()).hexdigest()[:12]
preview, scale = display_image(image)
box_prompts: list[BoxPrompt] = []
point_prompt: PointPrompt | None = None

st.subheader("1. Create a prompt")
if prompt_mode == "Area (recommended)":
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
else:
    st.caption("Click the object of interest. The last red marker is the active positive point prompt.")
    canvas = st_canvas(
        background_image=preview,
        drawing_mode="point",
        fill_color="rgba(220, 38, 38, 0.65)",
        stroke_color="#ffffff",
        stroke_width=2,
        point_display_radius=6,
        width=preview.width,
        height=preview.height,
        key=f"point-{image_id}",
    )
    if canvas.json_data and canvas.json_data.get("objects"):
        point_prompt = last_point_from_canvas(canvas.json_data["objects"], scale)
        if point_prompt is not None:
            st.success(f"Point: ({point_prompt.x:.0f}, {point_prompt.y:.0f})")

if not box_prompts and point_prompt is None:
    st.stop()

if st.button("2. Run MedSAM segmentation", type="primary"):
    paths = MedSAMPaths.from_environment()
    try:
        model, selected_device = cached_model(paths, device)
        with st.spinner(f"Encoding image and decoding the {prompt_mode.lower()} prompt on {selected_device}…"):
            embedding = encode_image(model, image, selected_device)
            if box_prompts:
                result = segment_from_box_prompts(model, embedding, box_prompts)
            else:
                result = segment_from_prompt(model, embedding, point_prompt)
    except (ModelConfigurationError, RuntimeError, ValueError) as error:
        st.error(str(error))
        st.stop()

    mask_image = mask_to_image(result.mask)
    overlay = overlay_mask(image, result.mask)
    original, mask = st.columns(2)
    with original:
        st.image(image, caption="Original image", width="stretch")
    with mask:
        st.image(mask_image, caption="Predicted mask", width="stretch")
    st.image(overlay, caption=f"MedSAM {result.prompt_kind}-prompt overlay", width="stretch")
    downloads = st.columns(2)
    with downloads[0]:
        st.download_button("Download mask PNG", image_png_bytes(mask_image), "medsam_mask.png", "image/png")
    with downloads[1]:
        st.download_button("Download overlay PNG", image_png_bytes(overlay), "medsam_overlay.png", "image/png")
