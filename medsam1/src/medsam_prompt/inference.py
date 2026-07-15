"""Prompt encoding and mask decoding for MedSAM image segmentation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image

from .preprocessing import ensure_rgb, image_to_medsam_input


@dataclass(frozen=True)
class BoxPrompt:
    x0: float
    y0: float
    x1: float
    y1: float

    def validate(self, width: int, height: int) -> None:
        if not (0 <= self.x0 < self.x1 <= width and 0 <= self.y0 < self.y1 <= height):
            raise ValueError("Draw a non-empty area fully inside the image.")


@dataclass(frozen=True)
class PointPrompt:
    x: float
    y: float
    label: Literal[0, 1] = 1

    def validate(self, width: int, height: int) -> None:
        if not (0 <= self.x < width and 0 <= self.y < height):
            raise ValueError("Click a point inside the image.")


@dataclass
class ImageEmbedding:
    embedding: object
    width: int
    height: int


@dataclass(frozen=True)
class SegmentationResult:
    mask: np.ndarray
    prompt_kind: str


def encode_image(model, image: Image.Image, device: str) -> ImageEmbedding:
    """Generate one reusable MedSAM image embedding for an uploaded image."""
    import torch

    rgb = ensure_rgb(image)
    model_input = image_to_medsam_input(rgb)
    tensor = torch.from_numpy(model_input).permute(2, 0, 1).unsqueeze(0).to(device=device, dtype=torch.float32)
    with torch.inference_mode():
        embedding = model.image_encoder(tensor)
    return ImageEmbedding(embedding=embedding, width=rgb.width, height=rgb.height)


def segment_from_prompt(model, image_embedding: ImageEmbedding, prompt: BoxPrompt | PointPrompt) -> SegmentationResult:
    """Decode a full-resolution binary mask from a box or positive/negative point."""
    import torch
    import torch.nn.functional as functional

    if isinstance(prompt, BoxPrompt):
        prompt.validate(image_embedding.width, image_embedding.height)
        coordinates = np.array([[prompt.x0, prompt.y0, prompt.x1, prompt.y1]], dtype=np.float32)
        scaled = coordinates / np.array(
            [image_embedding.width, image_embedding.height, image_embedding.width, image_embedding.height], dtype=np.float32
        ) * 1024
        boxes = torch.as_tensor(scaled, device=image_embedding.embedding.device)[:, None, :]
        points = None
        prompt_kind = "area"
    else:
        prompt.validate(image_embedding.width, image_embedding.height)
        coordinates = np.array([[[prompt.x, prompt.y]]], dtype=np.float32)
        scaled = coordinates / np.array([image_embedding.width, image_embedding.height], dtype=np.float32) * 1024
        point_coordinates = torch.as_tensor(scaled, device=image_embedding.embedding.device)
        point_labels = torch.as_tensor([[prompt.label]], device=image_embedding.embedding.device)
        points = (point_coordinates, point_labels)
        boxes = None
        prompt_kind = "point"

    with torch.inference_mode():
        sparse_embeddings, dense_embeddings = model.prompt_encoder(points=points, boxes=boxes, masks=None)
        logits, _ = model.mask_decoder(
            image_embeddings=image_embedding.embedding,
            image_pe=model.prompt_encoder.get_dense_pe(),
            sparse_prompt_embeddings=sparse_embeddings,
            dense_prompt_embeddings=dense_embeddings,
            multimask_output=False,
        )
        probabilities = torch.sigmoid(logits)
        resized = functional.interpolate(
            probabilities,
            size=(image_embedding.height, image_embedding.width),
            mode="bilinear",
            align_corners=False,
        )
    mask = resized.squeeze().detach().cpu().numpy() > 0.5
    return SegmentationResult(mask=mask, prompt_kind=prompt_kind)


def segment_from_box_prompts(
    model, image_embedding: ImageEmbedding, prompts: Sequence[BoxPrompt]
) -> SegmentationResult:
    """Decode each box against one image embedding and merge the masks."""
    if not prompts:
        raise ValueError("Draw at least one area before running segmentation.")
    for prompt in prompts:
        prompt.validate(image_embedding.width, image_embedding.height)

    masks = [segment_from_prompt(model, image_embedding, prompt).mask for prompt in prompts]
    return SegmentationResult(
        mask=np.logical_or.reduce(masks),
        prompt_kind="multi-area" if len(prompts) > 1 else "area",
    )
