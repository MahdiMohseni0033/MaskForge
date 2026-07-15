from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw

Point = tuple[float, float]


def _paint_circle(mask: np.ndarray, x: float, y: float, radius: float, class_id: int) -> None:
    height, width = mask.shape
    x0 = max(0, int(np.floor(x - radius)))
    x1 = min(width - 1, int(np.ceil(x + radius)))
    y0 = max(0, int(np.floor(y - radius)))
    y1 = min(height - 1, int(np.ceil(y + radius)))
    if x0 > x1 or y0 > y1:
        return
    yy, xx = np.ogrid[y0 : y1 + 1, x0 : x1 + 1]
    circle = (xx - x) ** 2 + (yy - y) ** 2 <= radius**2
    region = mask[y0 : y1 + 1, x0 : x1 + 1]
    region[circle] = class_id


def paint_stroke(
    mask: np.ndarray, points: Iterable[Point], brush_size: float, class_id: int
) -> np.ndarray:
    if mask.ndim != 2:
        raise ValueError("Mask must be two-dimensional")
    if brush_size < 1:
        raise ValueError("Brush size must be at least one pixel")
    if not 0 <= class_id <= np.iinfo(mask.dtype).max:
        raise ValueError("Class ID cannot be represented by the mask dtype")
    result = mask.copy()
    points = list(points)
    if not points:
        return result
    radius = brush_size / 2
    _paint_circle(result, *points[0], radius, class_id)
    spacing = max(0.5, radius / 2)
    for start, end in zip(points, points[1:], strict=False):
        distance = float(np.hypot(end[0] - start[0], end[1] - start[1]))
        steps = max(1, int(np.ceil(distance / spacing)))
        for step in range(1, steps + 1):
            fraction = step / steps
            _paint_circle(
                result,
                start[0] + (end[0] - start[0]) * fraction,
                start[1] + (end[1] - start[1]) * fraction,
                radius,
                class_id,
            )
    return result


def erase_stroke(mask: np.ndarray, points: Iterable[Point], brush_size: float) -> np.ndarray:
    return paint_stroke(mask, points, brush_size, 0)


def fill_polygon(mask: np.ndarray, vertices: Iterable[Point], class_id: int) -> np.ndarray:
    vertices = list(vertices)
    if len(vertices) < 3:
        raise ValueError("A polygon requires at least three vertices")
    if not 0 <= class_id <= np.iinfo(mask.dtype).max:
        raise ValueError("Class ID cannot be represented by the mask dtype")
    area = abs(
        sum(
            vertices[i][0] * vertices[(i + 1) % len(vertices)][1]
            - vertices[(i + 1) % len(vertices)][0] * vertices[i][1]
            for i in range(len(vertices))
        )
        / 2
    )
    if area < 0.5:
        raise ValueError("Polygon area is too small")
    selection = Image.new("1", (mask.shape[1], mask.shape[0]), 0)
    ImageDraw.Draw(selection).polygon(vertices, fill=1)
    inside = np.asarray(selection, dtype=bool)
    result = mask.copy()
    result[inside] = class_id
    return result


def clear_class(mask: np.ndarray, class_id: int) -> np.ndarray:
    result = mask.copy()
    result[result == class_id] = 0
    return result


def reset_mask(mask: np.ndarray) -> np.ndarray:
    return np.zeros_like(mask)


@dataclass
class MaskHistory:
    initial: np.ndarray
    limit: int = 30
    _states: list[np.ndarray] = field(init=False)
    _index: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self._states = [self.initial.copy()]

    @property
    def current(self) -> np.ndarray:
        return self._states[self._index].copy()

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return self._index + 1 < len(self._states)

    def push(self, mask: np.ndarray) -> None:
        self._states = self._states[: self._index + 1]
        self._states.append(mask.copy())
        if len(self._states) > self.limit + 1:
            self._states.pop(0)
        self._index = len(self._states) - 1

    def undo(self) -> np.ndarray:
        if self.can_undo:
            self._index -= 1
        return self.current

    def redo(self) -> np.ndarray:
        if self.can_redo:
            self._index += 1
        return self.current
