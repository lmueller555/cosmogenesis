"""Wireframe renderer for Cosmogenesis entities."""
from __future__ import annotations

from typing import Tuple

from OpenGL import GL as gl

from game.camera import Camera2D
from game.world import World
from .opengl_context import LINE_COLOR
from .wireframe_primitives import WireframeMesh, create_astral_citadel_mesh, create_planetoid_mesh


class WireframeRenderer:
    """Handles drawing of world entities using shared mesh data."""

    def __init__(self) -> None:
        self.planetoid_mesh = create_planetoid_mesh(radius=60.0)
        self.astral_citadel_mesh = create_astral_citadel_mesh()

    def draw_world(self, world: World, camera: Camera2D) -> None:
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glColor4f(*LINE_COLOR)

        for planetoid in world.planetoids:
            scale = planetoid.radius / 60.0
            self._draw_mesh(self.planetoid_mesh, planetoid.position, scale, camera)

        for base in world.bases:
            self._draw_mesh(self.astral_citadel_mesh, base.position, 1.0, camera)

    def _draw_mesh(self, mesh: WireframeMesh, position: Tuple[float, float], scale: float, camera: Camera2D) -> None:
        gl.glBegin(gl.GL_LINES)
        for start_index, end_index in mesh.segments:
            sx, sy = mesh.vertices[start_index]
            ex, ey = mesh.vertices[end_index]

            start_world = (position[0] + sx * scale, position[1] + sy * scale)
            end_world = (position[0] + ex * scale, position[1] + ey * scale)

            start_screen = camera.world_to_screen(start_world)
            end_screen = camera.world_to_screen(end_world)

            gl.glVertex2f(*start_screen)
            gl.glVertex2f(*end_screen)
        gl.glEnd()
