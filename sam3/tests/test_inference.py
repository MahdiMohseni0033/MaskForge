import numpy as np
from PIL import Image
import pytest

import sam3_app.inference as inference
from sam3_app.inference import BoxPrompt, run_inference
from sam3_app.models import LoadedSAM3


class FakeProcessor:
    def set_image(self, image: Image.Image) -> dict:
        return {"size": image.size}


class FakeModel:
    def __init__(self) -> None:
        self.boxes = None

    def predict_inst(self, state: dict, **kwargs):
        self.boxes = kwargs["box"]
        masks = np.array(
            [
                [[[True, False, False], [False, False, False]]],
                [[[False, True, False], [False, False, False]]],
            ]
        )
        return masks, np.array([[0.4], [0.8]]), np.zeros((2, 1, 2, 3))


def test_inference_batches_every_box_and_merges_masks(monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeModel()
    monkeypatch.setattr(inference, "create_processor", lambda loaded: FakeProcessor())

    result = run_inference(
        LoadedSAM3(model=model, device="cpu"),
        Image.new("RGB", (3, 2)),
        [BoxPrompt(0, 0, 1, 1), BoxPrompt(1, 0, 3, 2)],
    )

    assert model.boxes.tolist() == [[0, 0, 1, 1], [1, 0, 3, 2]]
    assert result.mask.dtype == bool
    assert result.mask.shape == (2, 3)
    assert result.mask.tolist() == [[True, True, False], [False, False, False]]
    assert result.instance_count == 2
    assert result.mean_quality == pytest.approx(0.6)


def test_inference_requires_at_least_one_box() -> None:
    with pytest.raises(ValueError, match="at least one"):
        run_inference(LoadedSAM3(object(), "cpu"), Image.new("RGB", (3, 2)), [])
