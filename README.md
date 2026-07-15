# MaskForge

MaskForge is a local workspace for medical-image segmentation research and manual 2D mask
annotation. It brings the related applications into one repository while keeping their Python
environments, upstream model sources, checkpoints, and runtime outputs isolated.

## Applications

- `segmentation_labeler/`: FastAPI, SQLite, React, TypeScript, and Konva application for manual
  class-indexed semantic segmentation labeling, autosave/resume, and mask export.
- `medsam1/`: official MedSAM ViT-B Streamlit prototype with rectangle and experimental point
  prompts.
- `medsam3/`: official MedSAM 3 base model with MedSAM3-v1 LoRA weights and native positive
  rectangle prompts.
- `sam3/`: official Meta SAM 3 Streamlit prototype with native rectangle prompts.

Each application remains self-contained. Run installation, validation, and startup commands from
the relevant directory so its project-relative paths and environment resolve correctly. See each
application's README for exact commands.

For the manual labeler:

```bash
cd segmentation_labeler
uv sync --dev
npm --prefix frontend install
make run
```

For a Streamlit prototype:

```bash
cd medsam1   # or: cd medsam3, cd sam3
conda activate "$PWD/.venv"
streamlit run app.py
```

## Repository hygiene

The root `.gitignore` excludes virtual environments, downloaded upstream repositories, model
checkpoints and weights, datasets, annotation databases, exports, results, logs, caches, frontend
dependencies, test artifacts, and secrets. Keep only de-identified data outside Git even when a
file is not explicitly matched by an ignore rule.

These applications are technical research prototypes and are not clinically validated medical
devices.
