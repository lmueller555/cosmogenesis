"""OpenGL context helpers for Cosmogenesis wireframe rendering."""
from __future__ import annotations

from typing import Tuple

from OpenGL import GL as gl


BACKGROUND_COLOR = (0.02, 0.02, 0.05, 1.0)
LINE_COLOR = (0.65, 0.85, 1.0, 1.0)


def initialize_gl(surface_size: Tuple[int, int]) -> None:
    """Configure OpenGL state for simple 2D line rendering."""
    width, height = surface_size
    gl.glViewport(0, 0, width, height)
    gl.glClearColor(*BACKGROUND_COLOR)

    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    gl.glOrtho(0, width, 0, height, -1, 1)

    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()

    gl.glDisable(gl.GL_DEPTH_TEST)
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glLineWidth(1.5)


def resize_viewport(surface_size: Tuple[int, int]) -> None:
    """Update viewport and projection when the window changes size."""
    initialize_gl(surface_size)
