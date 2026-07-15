# Progress tracker

## Completed

- Created the initial MedSAM3 Streamlit project structure, isolated-environment definition, package metadata, ignore rules, and reusable modules.
- Integrated directly with official `Joey-S-Liu/MedSAM3` `SAM3LoRAInference` for text-guided SAM3 + MedSAM3-v1 LoRA inference.
- Added Streamlit upload/prompt/device/settings flow, mask and overlay rendering, downloads, and clear missing-resource errors.
- Added scripts to bootstrap upstream code, download official LoRA weights, optionally fetch WSeg wound images, and validate multi-image inference.
- Added lightweight preprocessing and visualisation unit tests.
- Documented installation, authentication, model sources, validation commands, limitations, and prototype safety warning in README.

## Sources and technical decisions

- Upstream code: https://github.com/Joey-S-Liu/MedSAM3
- LoRA weights: https://huggingface.co/lal-Joey/MedSAM3_v1
- Base model: Meta SAM3; Hugging Face authentication/access may be required.
- The application now uses SAM 3's native positive geometric prompts with the MedSAM3-v1 LoRA-adapted model.
- Every selected rectangle is decoded independently from one image encoding, and all retained instance masks are unioned into one output.
- Optional WSeg samples: https://huggingface.co/datasets/subbareddyoota/wseg_dataset. The linked publication reports MIT; verify terms before use.

## Commands run and outcomes

- `sed -n ... AGENT.md`: read complete bootstrap instructions.
- Repository inspection: only `AGENT.md` existed at start; no `tracker.md` and no Git repository were present.
- `git ls-remote ...`: failed because the shell environment could not resolve `github.com`.
- `srun --jobid=9376434 ...`: failed; Slurm controller could not confirm the allocation, so GPU access was not available.
- Created project-local `.venv` with Conda Forge and Python 3.11.15. The first creation was broken (`pyexpat`/`libexpat` undefined symbol) and was removed; the rebuilt environment imports `pyexpat` successfully.
- Installed this project package, pytest, and Streamlit 1.59.2 in `.venv`; `pip check` passed.
- `.venv/bin/python3.11 -m compileall -q app.py src scripts tests`: passed.
- `.venv/bin/python3.11 -m pytest -q`: passed (6 tests).
- `timeout 10 .venv/bin/streamlit run app.py --server.headless true --server.port 8502`: passed; Uvicorn started on port 8502 and was stopped after the smoke test.
- `.venv/bin/python3.11 scripts/bootstrap_medsam3.py --skip-install`: passed; cloned `third_party/MedSAM3` at `f79eef3f4ccfc880e63a0a5a758153137e75d34b`.
- `.venv/bin/python3.11 scripts/download_model.py`: passed; downloaded the official 71 MB `best_lora_weights.pt` to `third_party/MedSAM3/outputs/sam3_lora_full/`.
- Updated Streamlit image calls from deprecated `use_container_width=True` to `width="stretch"`.
- The original archived environment/setup was incomplete at this stage; the later rectangle-prompt validation below supersedes that status.

## Current limitations / remaining work

- Validate rectangle-prompt predictions on representative, de-identified medical images with appropriate expert review.
- The upstream image project declares the video-only `decord 0.6.0` wheel, whose metadata reports the current platform as unsupported even though it imports. This causes `pip check` to warn; rectangle image inference does not import or use it.

## Rectangle-prompt implementation (2026-07-14)

- Moved the archived project, upstream source, and LoRA weights into the top-level `medsam3/` application directory; retained the existing environment through `medsam3/.venv` to avoid duplicating gigabytes.
- Replaced text prompting with the upstream native `Sam3Processor.add_geometric_prompt()` API on the LoRA-adapted model. The UI now matches MedSAM 1's multi-rectangle canvas, coordinate scaling, merged mask, overlay, and downloads.
- Confirmed experimentally that geometric prompting requires the fixed 1008-pixel encoder resolution; 512 produced an upstream rotary-position assertion, so invalid resolution choices were removed.
- Installed the drawable-canvas component and Streamlit compatibility adapter. Compile checks and 9 unit tests passed, and an uploaded-image Streamlit `AppTest` reached the rectangle canvas without exceptions.
- In Slurm allocation `9376732` on an NVIDIA H100 80GB, Hugging Face authentication, base SAM 3 loading, all 458 LoRA module adaptations, official MedSAM3-v1 weight loading, and native two-box inference passed. The synthetic-image result was a `(96, 128)` Boolean mask with 171 returned instance masks at threshold 0.1.
- Repeated the real two-box H100 inference with the UI defaults (threshold 0.5, resolution 1008): passed with a `(96, 128)` Boolean mask, 3 retained instance masks, and maximum score `0.730977`.
- Both `medsam1` and `medsam3` headless Streamlit servers started successfully on ports 8505 and 8506. Activating `medsam3/.venv` resolves the correct Python, Streamlit executable, and editable `medsam3_app` package.
