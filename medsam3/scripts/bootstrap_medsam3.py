#!/usr/bin/env python3
"""Clone and install the official MedSAM3 repository into this project."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


UPSTREAM_URL = "https://github.com/Joey-S-Liu/MedSAM3.git"


def run(command: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="main", help="Upstream git ref to clone (default: main).")
    parser.add_argument("--skip-install", action="store_true", help="Clone only; do not run pip install.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    destination = root / "third_party" / "MedSAM3"
    if destination.exists():
        print(f"Using existing upstream repository: {destination}")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--branch", args.ref, "--depth", "1", UPSTREAM_URL, str(destination)])
    run(["git", "rev-parse", "HEAD"], cwd=destination)
    if not args.skip_install:
        run([sys.executable, "-m", "pip", "install", "-e", "."], cwd=destination)
        print("MedSAM3 installed. Authenticate with `hf auth login`, then run scripts/download_model.py.")


if __name__ == "__main__":
    main()
