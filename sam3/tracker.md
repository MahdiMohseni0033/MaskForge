# Progress tracker

## Implementation

- Created an independent SAM 3 Streamlit application matching the sibling projects' rectangle-canvas, merged-mask, overlay, and download workflow.
- Integrated the official `facebookresearch/sam3` image model and native instance-interactive box predictor.

## Sources

- Upstream code: https://github.com/facebookresearch/sam3 (MIT licence)
- Checkpoint: https://huggingface.co/facebook/sam3 (access approval and authentication may be required)

## Validation

- Created an isolated Conda environment at `.venv` with Python 3.12.13 and user-site packages disabled.
- Installed PyTorch `2.10.0+cu128`, torchvision `0.25.0+cu128`, the Streamlit project, and the official SAM 3 package.
- Cloned official source commit `5dd401d1c5c1d5c3eedff06d41b77af824517619` into ignored `third_party/sam3`; the checkout remained clean.
- Added runtime pins for dependencies imported by the current official image-model path but absent from its base package metadata (`einops`, `pycocotools`, `psutil`, and `setuptools<81` for `pkg_resources`). The upstream source was not modified.
- `python -m compileall -q app.py src scripts tests`: passed.
- Final `python -m pytest -q`: passed (12 tests), including the uploaded-image canvas regression.
- `python -m pip check`: passed with no broken requirements.
- Official `sam3` and `Sam3Processor` imports passed from the official checkout.
- Headless Streamlit startup passed inside the H100 allocation on port 8507; Uvicorn started and stopped cleanly.
- Entered the allocation using `srun --jobid=9376732 --overlap --pty /bin/bash`; host `gpu121` exposed an NVIDIA H100 80GB HBM3 with driver `595.71.05`.
- Inside the allocation, Python 3.12.13 and PyTorch `2.10.0+cu128` reported CUDA 12.8 and `torch.cuda.is_available() == True`.
- Loaded the gated official `facebook/sam3` checkpoint from the authenticated Hugging Face cache and ran two `xyxy` boxes on upstream `assets/images/truck.jpg` through the application inference path.
- H100 inference passed: two masks were returned and merged into a `(1200, 1800)` Boolean mask with mean predicted quality `0.978515625`.
- Instrumented H100 rerun confirmed `loaded.device == "cuda"`, the first model parameter on `cuda:0`, 3.490 GiB allocated after loading, and 4.550 GiB peak CUDA allocation. Model loading took 9.172 seconds and the full two-box inference took 1.000 second.
- Output validation passed: the mask PNG was mode `L`, size `(1800, 1200)`, and non-empty; the overlay PNG was mode `RGB` with the same size.
- A Streamlit `AppTest` with a 64×48 uploaded PNG reached `1. Create area prompts` with zero exceptions; this is retained as an automated regression.

## Remaining evaluation

- Segmentation quality on representative de-identified medical images requires appropriate expert review; the successful technical checks are not clinical validation.
