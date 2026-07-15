#!/usr/bin/env python3
"""Download official MedSAM3-v1 LoRA weights into the upstream default location."""

from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import snapshot_download


MODEL_ID = "lal-Joey/MedSAM3_v1"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    repository = Path(os.environ.get("MEDSAM3_REPO_DIR", root / "third_party" / "MedSAM3"))
    if not (repository / "configs" / "full_lora_config.yaml").is_file():
        raise SystemExit("MedSAM3 upstream code is missing. Run scripts/bootstrap_medsam3.py first.")
    destination = repository / "outputs" / "sam3_lora_full"
    destination.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_ID} to {destination}")
    snapshot_download(repo_id=MODEL_ID, local_dir=destination)
    expected = destination / "best_lora_weights.pt"
    if not expected.is_file():
        raise SystemExit(f"Download completed but expected LoRA file was not found: {expected}")
    print(f"Ready: {expected}")
    print("The base SAM3 checkpoint will be fetched by the official loader on first model load; `hf auth login` is required.")


if __name__ == "__main__":
    main()
