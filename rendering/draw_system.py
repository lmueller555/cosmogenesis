"""Wireframe renderer for Cosmogenesis entities."""
from __future__ import annotations

from typing import Dict, Tuple

from OpenGL import GL as gl

from game.camera import Camera2D
from game.world import World
from .opengl_context import LINE_COLOR
from .wireframe_primitives import (
    WireframeMesh,
    create_astral_citadel_mesh,
    create_planetoid_mesh,
    create_abyssal_crown_mesh,
    create_daggerwing_mesh,
    create_iron_halberd_mesh,
    create_lance_of_dawn_mesh,
    create_oblivion_spire_mesh,
    create_spearling_mesh,
    create_star_fortress_mesh,
    create_sunlance_mesh,
    create_titans_ward_mesh,
    create_auric_veil_mesh,
    create_warden_mesh,
    create_wisp_mesh,
)


class WireframeRenderer:
    """Handles drawing of world entities using shared mesh data."""

    def __init__(self) -> None:
        self.planetoid_mesh = create_planetoid_mesh(radius=60.0)
        self.astral_citadel_mesh = create_astral_citadel_mesh()
        self.ship_meshes: Dict[str, WireframeMesh] = {
            "Spearling": create_spearling_mesh(),
            "Wisp": create_wisp_mesh(),
            "Daggerwing": create_daggerwing_mesh(),
            "Warden": create_warden_mesh(),
            "Sunlance": create_sunlance_mesh(),
            "Auric Veil": create_auric_veil_mesh(),
            "Iron Halberd": create_iron_halberd_mesh(),
            "Star Fortress": create_star_fortress_mesh(),
            "Lance of Dawn": create_lance_of_dawn_mesh(),
            "Titan's Ward": create_titans_ward_mesh(),
            "Abyssal Crown": create_abyssal_crown_mesh(),
            "Oblivion Spire": create_oblivion_spire_mesh(),
        }

    def draw_world(self, world: World, camera: Camera2D) -> None:
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glColor4f(*LINE_COLOR)

        for planetoid in world.planetoids:
            scale = planetoid.radius / 60.0
            self._draw_mesh(self.planetoid_mesh, planetoid.position, scale, camera)

        for base in world.bases:
            self._draw_mesh(self.astral_citadel_mesh, base.position, 1.0, camera)

        for ship in world.ships:
            mesh = self.ship_meshes.get(ship.definition.name)
            if mesh is None:
                # TODO: add visual fallback for ships without bespoke wireframes.
                continue
            scale = self._ship_scale_for(ship.definition.ship_class)
            self._draw_mesh(mesh, ship.position, scale, camera)

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

    @staticmethod
    def _ship_scale_for(ship_class: str) -> float:
        """Rudimentary scaling so larger classes feel bigger on screen."""

        if ship_class == "Strike":
            return 0.7
        if ship_class == "Escort":
            return 1.0
        if ship_class == "Line":
            return 1.3
        if ship_class == "Capital":
            return 1.6
        return 1.0
