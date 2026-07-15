from __future__ import annotations

import numpy as np
import pytest
from seglabeler.mask_ops import (
    MaskHistory,
    clear_class,
    erase_stroke,
    fill_polygon,
    paint_stroke,
    reset_mask,
)


def test_brush_eraser_and_overlapping_classes() -> None:
    mask = np.zeros((48, 64), dtype=np.uint16)
    mask = paint_stroke(mask, [(5, 12), (55, 12)], brush_size=7, class_id=1)
    assert mask[12, 5] == 1
    assert mask[12, 30] == 1  # interpolation prevents gaps

    mask = fill_polygon(mask, [(18, 8), (45, 8), (45, 35), (18, 35)], class_id=2)
    assert mask[20, 30] == 2
    assert mask[12, 10] == 1

    mask = erase_stroke(mask, [(30, 4), (30, 39)], brush_size=5)
    assert mask[20, 30] == 0
    assert set(np.unique(mask)) == {0, 1, 2}


def test_polygon_validation_clear_and_reset() -> None:
    mask = np.zeros((20, 20), dtype=np.uint16)
    with pytest.raises(ValueError, match="at least three"):
        fill_polygon(mask, [(1, 1), (3, 3)], 1)
    with pytest.raises(ValueError, match="too small"):
        fill_polygon(mask, [(1, 1), (2, 2), (3, 3)], 1)

    mask = fill_polygon(mask, [(2, 2), (17, 2), (10, 17)], 4)
    mask = paint_stroke(mask, [(1, 19)], 3, 7)
    cleared = clear_class(mask, 4)
    assert 4 not in np.unique(cleared)
    assert 7 in np.unique(cleared)
    assert not reset_mask(cleared).any()


def test_history_treats_states_as_logical_operations() -> None:
    initial = np.zeros((8, 8), dtype=np.uint16)
    history = MaskHistory(initial, limit=3)
    first = paint_stroke(initial, [(2, 2)], 3, 1)
    second = fill_polygon(first, [(3, 3), (7, 3), (7, 7)], 2)
    history.push(first)
    history.push(second)

    assert history.can_undo
    np.testing.assert_array_equal(history.undo(), first)
    np.testing.assert_array_equal(history.undo(), initial)
    assert not history.can_undo
    np.testing.assert_array_equal(history.redo(), first)

    replacement = clear_class(first, 1)
    history.push(replacement)
    assert not history.can_redo
