"""Compatibility helpers for the drawable-canvas Streamlit component."""

from __future__ import annotations

from typing import Any

import streamlit_drawable_canvas as drawable_canvas


def _install_canvas_image_url_compatibility() -> None:
    if hasattr(drawable_canvas.st_image, "image_to_url"):
        return

    from streamlit.elements.lib.image_utils import image_to_url
    from streamlit.elements.lib.layout_utils import LayoutConfig

    class _ImageCompatibility:
        @staticmethod
        def image_to_url(
            image: Any,
            width: int,
            clamp: bool,
            channels: str,
            output_format: str,
            image_id: str,
        ) -> str:
            return image_to_url(
                image,
                layout_config=LayoutConfig(width=width),
                clamp=clamp,
                channels=channels,
                output_format=output_format,
                image_id=image_id,
            )

    drawable_canvas.st_image = _ImageCompatibility()


_install_canvas_image_url_compatibility()
st_canvas = drawable_canvas.st_canvas

__all__ = ["st_canvas"]
