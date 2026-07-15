# SAM 3 Streamlit project guidance

Before modifying the project, read `tracker.md`, inspect the repository state, and verify rather than assume prior results.

## Architecture

- `app.py` is the Streamlit entry point; reusable logic belongs in `src/sam3_app/`.
- This project uses only the official `facebookresearch/sam3` source and `facebook/sam3` checkpoint. Do not substitute MedSAM or MedSAM3 weights.
- Preserve native box prompting through SAM 3's instance-interactive image predictor and its fixed 1008-pixel encoder resolution.
- Keep upstream source in ignored `third_party/sam3`, checkpoints in ignored/cache locations, and machine-specific paths in `SAM3_REPO_DIR` and `SAM3_CHECKPOINT`.
- Use GPU automatically when PyTorch exposes it; retain an explicit CPU option and do not claim GPU testing without a successful run.

## Quality and safety

- Keep modules small, typed where useful, and validate image inputs and output mask dimensions/dtype.
- Use the isolated environment declared in `environment.yml`; keep README commands current.
- Never commit checkpoints, upstream repositories, uploaded images, outputs, caches, logs, or credentials.
- Treat uploaded images as sensitive. Use only de-identified data and state that this is a technical prototype, not a clinically validated medical device.

## Validation and documentation

- At minimum run syntax/import checks, unit tests, multi-box inference, output validation, and a Streamlit startup check after changes.
- Confirm a current Slurm allocation and GPU/PyTorch availability before GPU work; do not interfere with other jobs.
- Record meaningful commands, outcomes, versions, sources/licences, blockers, and remaining validation in `tracker.md`.
