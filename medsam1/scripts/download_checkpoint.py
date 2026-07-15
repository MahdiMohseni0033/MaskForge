#!/usr/bin/env python3
"""Download the official MedSAM ViT-B checkpoint from Google Drive."""

from __future__ import annotations

from pathlib import Path

import gdown


# Official `medsam_vit_b.pth` file listed in bowang-lab/MedSAM's checkpoint folder.
CHECKPOINT_FILE_ID = "1UAmWL88roYR7wKlnApw5Bcuzf2iQgk6_"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    destination = root / "checkpoints"
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "medsam_vit_b.pth"
    if target.is_file() and target.stat().st_size > 100_000_000:
        print(f"Checkpoint already present: {target}")
        return
    downloaded = gdown.download(id=CHECKPOINT_FILE_ID, output=str(target), quiet=False)
    if not downloaded or not target.is_file() or target.stat().st_size < 100_000_000:
        raise SystemExit("The official checkpoint download did not complete. Retry the command from a persistent shell.")
    print(f"Ready: {target}")


if __name__ == "__main__":
    main()
