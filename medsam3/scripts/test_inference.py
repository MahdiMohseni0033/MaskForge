#!/usr/bin/env python3
"""Run rectangle-prompted MedSAM 3 inference on every image in a directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from medsam3_app import BoxPrompt, InferenceSettings, MedSAM3Paths, load_medsam3_model, run_inference
from medsam3_app.preprocessing import ensure_rgb
from medsam3_app.visualization import make_overlay, mask_to_image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, default=Path("sample_data/wseg"))
    parser.add_argument(
        "--box",
        type=float,
        nargs=4,
        action="append",
        required=True,
        metavar=("X0", "Y0", "X1", "Y1"),
        help="Source-image rectangle; repeat for multiple prompts.",
    )
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/inference"))
    args = parser.parse_args()
    suffixes = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    images = sorted(path for path in args.images.rglob("*") if path.suffix.lower() in suffixes)
    if not images:
        raise SystemExit(f"No supported images found in {args.images}")

    settings = InferenceSettings(args.threshold)
    paths = MedSAM3Paths.from_environment()
    model = load_medsam3_model(
        paths,
        device=args.device,
        threshold=args.threshold,
        resolution=1008,
    )
    prompts = [BoxPrompt(*box) for box in args.box]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for image_path in images:
        image = ensure_rgb(Image.open(image_path))
        result = run_inference(model, paths, image, prompts, settings)
        if result.mask.shape != (image.height, image.width) or result.mask.dtype != bool:
            raise RuntimeError(f"Invalid mask from {image_path}: {result.mask.shape}, {result.mask.dtype}")
        mask_to_image(result.mask).save(args.output_dir / f"{image_path.stem}_mask.png")
        make_overlay(image, result.mask).save(args.output_dir / f"{image_path.stem}_overlay.png")
        print(f"{image_path.name}: {result.instance_count} instances; mask {result.mask.shape} {result.mask.dtype}")


if __name__ == "__main__":
    main()
