#!/usr/bin/env python3
"""Run official SAM 3 rectangle inference on one or more images."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from sam3_app import BoxPrompt, SAM3Paths, load_sam3_model, run_inference
from sam3_app.preprocessing import ensure_rgb
from sam3_app.visualization import make_overlay, mask_to_image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True, help="Image file or directory.")
    parser.add_argument(
        "--box",
        type=float,
        nargs=4,
        action="append",
        required=True,
        metavar=("X0", "Y0", "X1", "Y1"),
        help="Source-image rectangle; repeat for multiple areas.",
    )
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/inference"))
    args = parser.parse_args()

    suffixes = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    if args.images.is_file():
        images = [args.images]
    else:
        images = sorted(path for path in args.images.rglob("*") if path.suffix.lower() in suffixes)
    if not images:
        raise SystemExit(f"No supported images found at {args.images}")

    loaded = load_sam3_model(SAM3Paths.from_environment(), device=args.device)
    prompts = [BoxPrompt(*box) for box in args.box]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for image_path in images:
        image = ensure_rgb(Image.open(image_path))
        result = run_inference(loaded, image, prompts)
        if result.mask.shape != (image.height, image.width) or result.mask.dtype != bool:
            raise RuntimeError(f"Invalid mask from {image_path}: {result.mask.shape}, {result.mask.dtype}")
        mask_to_image(result.mask).save(args.output_dir / f"{image_path.stem}_mask.png")
        make_overlay(image, result.mask).save(args.output_dir / f"{image_path.stem}_overlay.png")
        print(
            f"{image_path.name}: {result.instance_count} masks; "
            f"mask {result.mask.shape} {result.mask.dtype}; mean quality {result.mean_quality}"
        )


if __name__ == "__main__":
    main()
