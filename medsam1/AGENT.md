# MedSAM prompt application guidance

Read `tracker.md` before working and verify the current state rather than assuming a model or allocation is ready.

## Architecture

- This root project uses the official `bowang-lab/MedSAM` source at ignored `third_party/MedSAM` and its ViT-B checkpoint at ignored `checkpoints/medsam_vit_b.pth`.
- Keep reusable logic in `src/medsam_prompt/`; `app.py` should remain only the Streamlit interface.
- The native MedSAM workflow is area (bounding-box) prompted. A positive point mode is exposed through the SAM prompt encoder, but its quality must not be represented as equivalent to box-prompt quality without validation.
- Do not substitute another segmentation model. Keep source/checkpoint paths configurable through `MEDSAM_REPO_DIR` and `MEDSAM_CHECKPOINT`.

## Environment, data, and safety

- Use the isolated environment declared in `environment.yml`. Install a CUDA-compatible PyTorch build appropriate to the active H100 allocation before installing the MedSAM package with `scripts/bootstrap_medsam.py`.
- Exclude environments, checkpoints, third-party source, sample images, outputs, logs, and credentials from Git.
- Treat uploaded images as sensitive; use de-identified images only. The application is a technical research prototype, not a clinically validated medical device.
- Do not claim GPU inference, model loading, or clinical quality without an executed validation.

## Validation and documentation

- Maintain concise progress, commands, outcomes, source details, and blockers in `tracker.md`.
- After changes, run syntax/import checks, unit tests, Streamlit startup, and multi-image inference once the checkpoint and GPU are available.
- Confirm Slurm allocation and `nvidia-smi`/`torch.cuda.is_available()` inside that allocation before GPU testing. Do not disturb other jobs.
