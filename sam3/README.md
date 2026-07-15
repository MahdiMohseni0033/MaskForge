# SAM 3 rectangle-prompt segmentation

A Streamlit technical prototype using the official [facebookresearch/sam3](https://github.com/facebookresearch/sam3) source and `facebook/sam3` checkpoint. Upload an image, draw one or more area prompts, and download the merged binary mask or overlay.

This is not a clinically validated medical device and must not be used for diagnosis, triage, measurement, or treatment decisions.

## Prompt implementation

The application follows the upstream SAM 1-task image example: it builds SAM 3 with instance interactivity enabled, computes one image embedding with `Sam3Processor.set_image()`, and sends all selected rectangles as source-image `xyxy` boxes to `predict_inst()`. SAM 3 returns one mask per box and the application merges them into a single mask. The encoder uses the official fixed 1008-pixel resolution.

## Setup

The official repository currently requires Python 3.12+, PyTorch 2.7+, and CUDA 12.6+ for GPU operation. From this directory:

```bash
conda create --prefix .venv --override-channels -c conda-forge python=3.12 pip -y
conda env config vars set --prefix .venv PYTHONNOUSERSITE=1
conda activate "$PWD/.venv"
python -m pip install torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128
python -m pip install -e ".[dev]"
python scripts/bootstrap_sam3.py
```

The user-site exclusion keeps this environment independent from other Python 3.12 installations on the same machine.

Request access to the gated [facebook/sam3 checkpoint](https://huggingface.co/facebook/sam3), then authenticate if it is not already cached:

```bash
hf auth login
```

The official loader downloads the checkpoint from Hugging Face on first use. To use a local checkpoint or a different official source checkout:

```bash
export SAM3_CHECKPOINT=/path/to/sam3.pt
export SAM3_REPO_DIR=/path/to/facebookresearch/sam3
```

## Run

```bash
cd /mnt/scratch2/users/mmohseni/projects/medsam3/sam3
conda activate "$PWD/.venv"
streamlit run app.py
```

1. Upload a de-identified PNG, JPEG, or TIFF image.
2. Draw one or more rectangles around the targets.
3. Select `auto` or `cuda`, then run segmentation.
4. Inspect and download the merged mask or overlay.

## Validation

```bash
python -m compileall app.py src scripts tests
pytest -q
python -m pip check
streamlit run app.py --server.headless true
```

Run a direct multi-box check with source-image coordinates:

```bash
python scripts/test_inference.py --images /path/to/de-identified/image.png \
  --box 20 30 220 260 --box 300 100 480 340 --device cuda
```

For GPU validation, connect to the current allocation first:

```bash
srun --jobid=9376732 --overlap --pty /bin/bash
cd /mnt/scratch2/users/mmohseni/projects/medsam3/sam3
conda activate "$PWD/.venv"
nvidia-smi
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

Only de-identified images should be used. Successful technical inference does not establish medical accuracy or clinical suitability.
