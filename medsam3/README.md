# MedSAM 3 rectangle-prompt segmentation

A Streamlit technical prototype using the official `Joey-S-Liu/MedSAM3` source, Meta SAM 3 base checkpoint, and `lal-Joey/MedSAM3_v1` LoRA weights. Upload an image, draw one or more positive rectangles, and download the merged binary mask or overlay.

This is not a clinically validated medical device and must not be used for diagnosis, triage, measurement, or treatment decisions.

## Prompt implementation

The app uses the upstream `Sam3Processor.add_geometric_prompt()` API. Canvas rectangles are converted from source-image `xyxy` pixels to normalized `cxcywh` boxes. The image backbone runs once; each box is decoded independently and all returned masks are merged. Native geometric inference requires SAM 3's fixed 1008×1008 encoder resolution.

## Run

The existing environment and model files are already connected to this directory:

```bash
cd /mnt/scratch2/users/mmohseni/projects/medsam3/medsam3
conda activate "$PWD/.venv"
streamlit run app.py
```

The first model load uses the gated `facebook/sam3` checkpoint from the authenticated Hugging Face cache. The LoRA weights default to `third_party/MedSAM3/outputs/sam3_lora_full/best_lora_weights.pt`.

For a fresh setup:

```bash
python -m pip install -e ".[dev]"
python scripts/bootstrap_medsam3.py
hf auth login
python scripts/download_model.py
```

Override non-default locations with `MEDSAM3_REPO_DIR`, `MEDSAM3_CONFIG`, or `MEDSAM3_LORA_WEIGHTS`.

## Validation

```bash
python -m compileall app.py src scripts tests
pytest -q
streamlit run app.py --server.headless true
```

For scripted inference, provide source-image boxes; repeat `--box` for multiple areas:

```bash
python scripts/test_inference.py --images sample_data/wseg \
  --box 20 30 220 260 --box 300 100 480 340 --device cuda
```

The interface accepts PNG, JPEG, and TIFF images. Use only de-identified data and validate predictions with qualified reviewers before any research interpretation.
