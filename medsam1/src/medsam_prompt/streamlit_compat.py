"""Compatibility helpers for third-party Streamlit components."""

from __future__ import annotations

from typing import Any

import streamlit_drawable_canvas as drawable_canvas


def _install_canvas_image_url_compatibility() -> None:
    """Adapt drawable-canvas to Streamlit's relocated image URL helper."""
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

    # drawable-canvas 0.9.3 imports the old streamlit.elements.image module
    # and calls its removed image_to_url helper when a background image is set.
    drawable_canvas.st_image = _ImageCompatibility()


_install_canvas_image_url_compatibility()
st_canvas = drawable_canvas.st_canvas

__all__ = ["st_canvas"]
