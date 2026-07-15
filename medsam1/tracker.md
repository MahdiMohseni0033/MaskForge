# Progress tracker

## Current implementation

- Archived the previous text-guided MedSAM3 prototype, including its environment and artefacts, under `archive/v1/`.
- Started a clean prompt-guided implementation using official MedSAM source: https://github.com/bowang-lab/MedSAM
- Cloned official source to ignored `third_party/MedSAM` at commit `d71e8a1a99ad751840a22a7fa3ecfb4166fb1488`.
- Added reusable image preprocessing, native area-prompt and single-point prompt inference, mask rendering, Streamlit UI, checkpoint downloader, package bootstrap script, tests, and documentation.
- Created a fresh project-local `.venv` with Python 3.11.15 and installed the Streamlit prompt UI, image, checkpoint-download, and test dependencies.
- Installed `torch==2.7.1` and `torchvision==0.22.1` with CUDA 12.6 runtime libraries into that environment.
- Downloaded the official 358 MB `checkpoints/medsam_vit_b.pth` checkpoint directly from the published MedSAM Google Drive file.

## Model details

- Model: MedSAM ViT-B, official checkpoint published by bowang-lab in its Google Drive folder.
- Native inference: bounding-box prompt. Point mode uses the underlying SAM point prompt encoder and must be treated as experimental for MedSAM.
- Checkpoint destination: `checkpoints/medsam_vit_b.pth` (ignored by Git).

## Commands and outcomes

- `srun --jobid=9376732 --overlap --pty /bin/bash`: passed on 2026-07-14; connected to `gpu121` (NVIDIA H100 80GB HBM3, 81,559 MiB, driver 595.71.05).
- `git clone --depth 1 https://github.com/bowang-lab/MedSAM.git third_party/MedSAM`: passed.
- `.venv/bin/python3.11 -m pytest -q`: passed (6 tests).
- `.venv/bin/python3.11 -m compileall -q app.py src scripts tests`: passed.
- `timeout 10 .venv/bin/streamlit run app.py --server.headless true --server.port 8503`: passed; Uvicorn started successfully and was stopped after the smoke test.
- `.venv/bin/python3.11 scripts/download_checkpoint.py`: passed; checkpoint saved at `checkpoints/medsam_vit_b.pth`.
- `.venv/bin/python3.11 -m pip check`: passed after avoiding the official repository's unused Jupyter/3D package metadata. The app imports `segment_anything` directly from the official source path at runtime.
- GPU validation: PyTorch `2.7.1+cu126` reported CUDA available on the H100. The official checkpoint loaded successfully and produced boolean masks of shape `(192, 256)` from both a box prompt and a positive point prompt.
- Final regression: `.venv/bin/python3.11 -m pip check` passed; `.venv/bin/python3.11 -m pytest -q` passed (6 tests).
- `timeout 10 .venv/bin/streamlit run app.py --server.headless true --server.port 8504`: passed from the H100 allocation; Uvicorn started successfully and was stopped after the smoke test.
- Added a local compatibility adapter for `streamlit-drawable-canvas 0.9.3`, whose background-image code calls a private image helper removed from `streamlit.elements.image` in current Streamlit releases.
- Compatibility regression: `.venv/bin/python -m compileall -q app.py src scripts tests`, `.venv/bin/python -m pytest -q` (7 tests), and `.venv/bin/python -m pip check` passed. A Streamlit `AppTest` upload reached the area canvas with no exception, and a headless server smoke test started successfully on port 8505.
- Added multi-area prompting: all rectangles are converted to source-image coordinates, decoded against one reusable image embedding, and merged into one boolean mask. Replaced the non-rendering point-coordinate widget with the working drawable canvas point mode and a visible marker.
- Multi-prompt regression: compile checks, `.venv/bin/python -m pytest -q` (10 tests), `.venv/bin/python -m pip check`, uploaded-image `AppTest` runs for both area and point modes, and a headless Streamlit startup on port 8505 passed.
- Real H100 regression in Slurm job `9376732`: the official checkpoint decoded two boxes into a merged `(96, 128)` boolean mask and decoded a positive point into a `(96, 128)` boolean mask from the same synthetic-image embedding.

## Remaining work

- Test point and box segmentation on representative, de-identified wound images, including expected clinical review of the resulting masks.
- Run a browser-level Streamlit interaction against the H100-backed app.

## Workspace reorganization

- Moved this complete MedSAM 1 application, official source checkout, and checkpoints into `medsam1/`. Its `.venv` entry points to the existing project environment to avoid duplicating 5.9 GB of packages.
