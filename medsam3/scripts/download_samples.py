#!/usr/bin/env python3
"""Optionally download a small, licensed wound-image sample set for technical testing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download


DATASET_ID = "subbareddyoota/wseg_dataset"
SOURCE_URL = f"https://huggingface.co/datasets/{DATASET_ID}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=3, help="Number of image files to download (default: 3).")
    args = parser.parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")

    root = Path(__file__).resolve().parents[1]
    destination = root / "sample_data" / "wseg"
    destination.mkdir(parents=True, exist_ok=True)
    image_suffixes = {".jpg", ".jpeg", ".png"}
    files = [
        filename
        for filename in HfApi().list_repo_files(DATASET_ID, repo_type="dataset")
        if Path(filename).suffix.lower() in image_suffixes and "mask" not in filename.lower()
    ]
    selected = files[: args.limit]
    if len(selected) < args.limit:
        raise SystemExit(f"Only found {len(selected)} non-mask images in {DATASET_ID}.")
    for filename in selected:
        downloaded = hf_hub_download(DATASET_ID, filename, repo_type="dataset", local_dir=destination)
        print(f"Downloaded {downloaded}")
    metadata = {
        "dataset": DATASET_ID,
        "source_url": SOURCE_URL,
        "license": "MIT (as reported by the linked dataset publication; verify before redistribution)",
        "purpose": "Technical inference smoke testing only; not clinical validation.",
        "files": selected,
    }
    (destination / "SOURCE.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
