#!/usr/bin/env python3
"""Verify that the official MedSAM source tree is available to the application."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    repository = root / "third_party" / "MedSAM"
    if not (repository / "segment_anything").is_dir():
        raise SystemExit("Official MedSAM source is missing. Clone bowang-lab/MedSAM into third_party/MedSAM first.")
    print(f"Official MedSAM source ready: {repository}")
    print("Install the CUDA-compatible PyTorch stack before inference.")


if __name__ == "__main__":
    main()
