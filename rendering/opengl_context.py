"""OpenGL context helpers for Cosmogenesis wireframe rendering."""
from __future__ import annotations

from typing import Tuple

from OpenGL import GL as gl


BACKGROUND_COLOR = (0.02, 0.02, 0.05, 1.0)
LINE_COLOR = (0.65, 0.85, 1.0, 1.0)


def initialize_gl(surface_size: Tuple[int, int]) -> None:
    """Configure OpenGL state for 3D line rendering."""
    width, height = surface_size
    gl.glViewport(0, 0, width, height)
    gl.glClearColor(*BACKGROUND_COLOR)

    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_LEQUAL)
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glLineWidth(1.5)


def resize_viewport(surface_size: Tuple[int, int]) -> None:
    """Update viewport when the window changes size."""
    width, height = surface_size
    gl.glViewport(0, 0, width, height)
