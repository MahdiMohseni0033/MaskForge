# MedSAM prompt segmentation

A Streamlit technical prototype using the official [MedSAM](https://github.com/bowang-lab/MedSAM) ViT-B model. It segments an uploaded 2D image from either:

- one or more **area prompts**: draw rectangles around the targets (the native MedSAM workflow and recommended mode), whose predicted masks are merged; or
- a **positive point prompt**: click the target (implemented through the underlying SAM prompt encoder; validate quality for the intended data).

This is not a clinically validated medical device. Do not use it for diagnosis, triage, treatment decisions, or clinical measurement.

## Model and source

- Source: `bowang-lab/MedSAM`, Apache-2.0. It is cloned to ignored `third_party/MedSAM`.
- Checkpoint: the official MedSAM ViT-B checkpoint linked from the upstream repository. The downloader fetches its published file directly to ignored `checkpoints/medsam_vit_b.pth`.
- The app uses `sam_model_registry["vit_b"]` from the official source; it does not substitute another model.

## Environment setup

The H100 requires a CUDA-enabled PyTorch build. Start from the project root and create a fresh local Conda environment:

```bash
conda create --prefix .venv --override-channels -c conda-forge python=3.11 pip -y
conda activate /mnt/scratch2/users/mmohseni/projects/medsam3/.venv
python -m pip install torch==2.7.1 torchvision==0.22.1
python -m pip install -e ".[dev]"
python scripts/bootstrap_medsam.py
python scripts/download_checkpoint.py
```

The PyTorch command selects the CUDA 12 wheel published on PyPI. Verify that it is compatible with the active H100 allocation before use:

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

If the checkpoint is already stored elsewhere, set its location rather than copying it:

```bash
export MEDSAM_REPO_DIR=/path/to/MedSAM
export MEDSAM_CHECKPOINT=/path/to/medsam_vit_b.pth
```

## Launch

```bash
conda activate /mnt/scratch2/users/mmohseni/projects/medsam3/.venv
streamlit run app.py
```

1. Upload a de-identified PNG, JPEG, or TIFF image.
2. Choose **Area (recommended)** and draw one or more rectangles around the targets, or choose **Point** and click the target.
3. Select `auto` to use CUDA when it is available, then run segmentation.
4. Inspect and download the predicted mask or overlay.

The app computes the image embedding once for each run and reuses it while decoding every selected box. Multiple box masks are combined into one output. Draw sufficiently tight but inclusive boxes for the most reliable MedSAM workflow.

## Validation

Run source checks after installation:

```bash
python -m compileall app.py src scripts tests
pytest -q
streamlit run app.py --server.headless true
```

For GPU validation, first enter a current allocation (the job id may change):

```bash
srun --jobid=9376732 --overlap --pty /bin/bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Then use several de-identified images with different prompt locations and record the results in `tracker.md`. This validates technical behaviour only, not medical accuracy. Keep images and generated outputs out of Git.

## Troubleshooting

- **Checkpoint missing:** run `python scripts/download_checkpoint.py`, or set `MEDSAM_CHECKPOINT` to an existing file.
- **CUDA unavailable:** run `nvidia-smi` and the PyTorch check inside the actual Slurm allocation. Use CPU only as a slow fallback.
- **No useful mask from a point:** switch to an area prompt; the official MedSAM inference example is box prompted.
- **Area does not register:** make sure each rectangle starts and ends inside the displayed image; use the canvas reset control to clear all prompts and redraw them.
- **Out-of-memory error:** use a smaller image or select CPU only for troubleshooting. The model always encodes at 1024×1024.

## Archive

The superseded text-guided MedSAM3 project is preserved at `archive/v1/` and is not part of this implementation.
