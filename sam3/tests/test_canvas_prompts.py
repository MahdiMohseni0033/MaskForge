from sam3_app.canvas_prompts import boxes_from_canvas


def test_all_canvas_rectangles_become_box_prompts() -> None:
    objects = [
        {"type": "rect", "left": 10, "top": 20, "width": 30, "height": 40, "scaleX": 1, "scaleY": 1},
        {"type": "circle", "left": 1, "top": 2, "radius": 6},
        {"type": "rect", "left": 50, "top": 60, "width": 10, "height": 20, "scaleX": 2, "scaleY": 0.5},
    ]

    prompts = boxes_from_canvas(objects, scale=0.5)

    assert [(prompt.x0, prompt.y0, prompt.x1, prompt.y1) for prompt in prompts] == [
        (20, 40, 80, 120),
        (100, 120, 140, 140),
    ]
