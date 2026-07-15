"""Translate drawable-canvas objects into full-resolution MedSAM prompts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .inference import BoxPrompt, PointPrompt


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


def last_point_from_canvas(objects: Iterable[Mapping[str, Any]], scale: float) -> PointPrompt | None:
    """Return the most recently drawn point, mapped to source-image pixels."""
    if scale <= 0:
        raise ValueError("Canvas scale must be positive.")

    circles = [shape for shape in objects if shape.get("type") == "circle"]
    if not circles:
        return None

    shape = circles[-1]
    radius = float(shape["radius"])
    stroke_width = float(shape.get("strokeWidth", 0))
    left = float(shape["left"])
    top = float(shape["top"])
    # drawable-canvas stores point circles with left origin and vertical centre
    # origin. Its point tool offsets left by radius plus half the stroke width.
    x = left if shape.get("originX") == "center" else left + radius + stroke_width / 2
    y = top if shape.get("originY") == "center" else top + radius + stroke_width / 2
    return PointPrompt(x / scale, y / scale)
