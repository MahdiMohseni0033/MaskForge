"""Translate drawable-canvas rectangles into full-resolution box prompts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .inference import BoxPrompt


def boxes_from_canvas(objects: Iterable[Mapping[str, Any]], scale: float) -> list[BoxPrompt]:
    """Return every rectangle in canvas order, mapped to source-image pixels."""
    if scale <= 0:
        raise ValueError("Canvas scale must be positive.")

    prompts = []
    for shape in objects:
        if shape.get("type") != "rect":
            continue
        left = float(shape["left"])
        top = float(shape["top"])
        width = abs(float(shape["width"]) * float(shape.get("scaleX", 1)))
        height = abs(float(shape["height"]) * float(shape.get("scaleY", 1)))
        prompts.append(
            BoxPrompt(left / scale, top / scale, (left + width) / scale, (top + height) / scale)
        )
    return prompts
