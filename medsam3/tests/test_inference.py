from pathlib import Path

import numpy as np
from PIL import Image
import pytest

import medsam3_app.inference as inference
from medsam3_app.inference import BoxPrompt, InferenceSettings, run_inference
from medsam3_app.models import MedSAM3Paths


class FakeProcessor:
    def __init__(self) -> None:
        self.boxes: list[list[float]] = []

    def set_image(self, image: Image.Image) -> dict:
        return {"image_size": image.size}

    def reset_all_prompts(self, state: dict) -> None:
        state.pop("masks", None)
        state.pop("scores", None)

    def add_geometric_prompt(self, box: list[float], label: bool, state: dict) -> dict:
        assert label is True
        self.boxes.append(box)
        if len(self.boxes) == 1:
            state["masks"] = np.array([[[[True, False, False], [False, False, False]]]])
            state["scores"] = np.array([0.3])
        else:
            state["masks"] = np.array([[[[False, True, False], [False, False, False]]]])
            state["scores"] = np.array([0.8])
        return state


def test_inference_merges_every_box_and_preserves_image_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    processor = FakeProcessor()
    monkeypatch.setattr(inference, "create_box_processor", lambda *args, **kwargs: processor)
    paths = MedSAM3Paths(tmp_path, tmp_path / "config.yaml", tmp_path / "weights.pt")
    image = Image.new("RGB", (3, 2))

    result = run_inference(
        object(),
        paths,
        image,
        [BoxPrompt(0, 0, 1, 1), BoxPrompt(1, 0, 3, 2)],
        InferenceSettings(),
    )

    assert processor.boxes == [
        pytest.approx([1 / 6, 1 / 4, 1 / 3, 1 / 2]),
        pytest.approx([2 / 3, 1 / 2, 2 / 3, 1]),
    ]
    assert result.mask.dtype == bool
    assert result.mask.shape == (2, 3)
    assert result.mask.tolist() == [[True, True, False], [False, False, False]]
    assert result.instance_count == 2
    assert result.max_score == pytest.approx(0.8)


def test_inference_requires_at_least_one_box(tmp_path: Path) -> None:
    paths = MedSAM3Paths(tmp_path, tmp_path / "config.yaml", tmp_path / "weights.pt")
    with pytest.raises(ValueError, match="at least one"):
        run_inference(object(), paths, Image.new("RGB", (3, 2)), [], InferenceSettings())
