import numpy as np
import pytest

import medsam_prompt.inference as inference
from medsam_prompt.inference import BoxPrompt, ImageEmbedding, PointPrompt, SegmentationResult


def test_box_prompt_accepts_valid_area() -> None:
    BoxPrompt(1, 2, 10, 20).validate(width=12, height=24)


def test_box_prompt_rejects_empty_area() -> None:
    with pytest.raises(ValueError):
        BoxPrompt(4, 2, 4, 20).validate(width=12, height=24)


def test_point_prompt_rejects_out_of_bounds_click() -> None:
    with pytest.raises(ValueError):
        PointPrompt(12, 2).validate(width=12, height=24)


def test_multiple_box_masks_are_merged(monkeypatch: pytest.MonkeyPatch) -> None:
    masks = iter(
        [
            np.array([[True, False], [False, False]]),
            np.array([[False, False], [False, True]]),
        ]
    )

    def fake_segment(model, embedding, prompt):
        return SegmentationResult(next(masks), "area")

    monkeypatch.setattr(inference, "segment_from_prompt", fake_segment)
    embedding = ImageEmbedding(embedding=object(), width=2, height=2)
    result = inference.segment_from_box_prompts(
        object(), embedding, [BoxPrompt(0, 0, 1, 1), BoxPrompt(1, 1, 2, 2)]
    )

    assert result.prompt_kind == "multi-area"
    assert result.mask.tolist() == [[True, False], [False, True]]
