import pytest

from medsam_prompt.canvas_prompts import boxes_from_canvas, last_point_from_canvas


def test_all_canvas_rectangles_become_box_prompts() -> None:
    objects = [
        {
            "type": "rect",
            "left": 10,
            "top": 20,
            "width": 30,
            "height": 40,
            "scaleX": 1,
            "scaleY": 1,
        },
        {"type": "circle", "left": 1, "top": 2, "radius": 6},
        {
            "type": "rect",
            "left": 50,
            "top": 60,
            "width": 10,
            "height": 20,
            "scaleX": 2,
            "scaleY": 0.5,
        },
    ]

    prompts = boxes_from_canvas(objects, scale=0.5)

    assert [(prompt.x0, prompt.y0, prompt.x1, prompt.y1) for prompt in prompts] == [
        (20, 40, 80, 120),
        (100, 120, 140, 140),
    ]


def test_last_canvas_point_uses_marker_centre() -> None:
    objects = [
        {
            "type": "circle",
            "left": 3,
            "top": 4,
            "radius": 6,
            "strokeWidth": 2,
            "originX": "left",
            "originY": "center",
        },
        {
            "type": "circle",
            "left": 13,
            "top": 24,
            "radius": 6,
            "strokeWidth": 2,
            "originX": "left",
            "originY": "center",
        },
    ]

    prompt = last_point_from_canvas(objects, scale=0.5)

    assert prompt is not None
    assert prompt.x == pytest.approx(40)
    assert prompt.y == pytest.approx(48)
