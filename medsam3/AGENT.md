# MedSAM3 Streamlit project guidance

Before modifying the project, read `tracker.md`, inspect the repository state, and verify rather than assume prior results.

## Architecture

- `app.py` is the Streamlit entry point; reusable logic belongs in `src/medsam3_app/`.
- This project uses the official `Joey-S-Liu/MedSAM3` source and `lal-Joey/MedSAM3_v1` LoRA weights. Do not silently replace MedSAM3 with another model.
- The application uses the official SAM 3 geometric-prompt processor with the MedSAM3-v1 LoRA-adapted model. Preserve native positive rectangle prompting and the fixed 1008-pixel encoder resolution.
- Keep upstream source in ignored `third_party/MedSAM3`, model weights in ignored locations, and machine-specific paths in environment variables (`MEDSAM3_REPO_DIR`, `MEDSAM3_CONFIG`, `MEDSAM3_LORA_WEIGHTS`).
- Use GPU automatically when PyTorch exposes it; retain an explicit CPU option and do not claim GPU testing without a successful run.

## Quality and safety

- Keep modules small, typed where useful, and avoid hiding errors. Validate image inputs and output mask dimensions/dtype.
- Use the project Conda environment (`environment.yml`) rather than global installs. Keep dependencies and commands in README accurate.
- Never commit checkpoints, third-party repositories, downloaded clinical images, outputs, caches, logs, or credentials.
- Treat all images as sensitive. Use only de-identified data and state that this is a technical prototype, not a clinically validated medical device.
- Record meaningful commands, outcomes, versions, sources/licences, blockers, and remaining validation in `tracker.md`.

## Validation and documentation

- At minimum run syntax/import checks, unit tests, multi-image inference, output validation, and a Streamlit startup check after changes.
- Confirm a current Slurm allocation and GPU/PyTorch availability before GPU work; do not interfere with other jobs.
- Update README when setup, model sources, prompt behaviour, or commands change. Keep `AGENT.md` durable and `tracker.md` session-specific.
