"""Wireframe renderer for Cosmogenesis entities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from OpenGL import GL as gl

import math
import numpy as np
import pygame

from game.camera import Camera3D
from game.entities import Base, Facility
from game.world import World
from game.ship_registry import ShipDefinition
from ui.layout import UILayout
from .opengl_context import LINE_COLOR
from .wireframe_primitives import (
    WireframeMesh,
    create_astral_citadel_mesh,
    create_planetoid_mesh,
    create_asteroid_mesh,
    create_abyssal_crown_mesh,
    create_defense_grid_node_mesh,
    create_fleet_forge_mesh,
    create_daggerwing_mesh,
    create_iron_halberd_mesh,
    create_lance_of_dawn_mesh,
    create_oblivion_spire_mesh,
    create_research_nexus_mesh,
    create_shipwright_foundry_mesh,
    create_spearling_mesh,
    create_star_fortress_mesh,
    create_sunlance_mesh,
    create_titans_ward_mesh,
    create_auric_veil_mesh,
    create_warden_mesh,
    create_wisp_mesh,
    create_skimmer_drone_mesh,
)


@dataclass
class ShipBuildButton:
    definition: ShipDefinition
    rect: pygame.Rect
    enabled: bool


class WireframeRenderer:
    """Handles drawing of world entities using shared mesh data."""

    def __init__(self) -> None:
        pygame.font.init()
        self.planetoid_mesh = create_planetoid_mesh(radius=60.0)
        self.asteroid_mesh = create_asteroid_mesh(radius=24.0)
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
            "Skimmer Drone": create_skimmer_drone_mesh(),
        }
        self._ship_mesh_bounds: Dict[str, Tuple[float, float, float, float]] = {
            name: self._compute_mesh_bounds(mesh) for name, mesh in self.ship_meshes.items()
        }
        self.facility_meshes: Dict[str, WireframeMesh] = {
            "ShipwrightFoundry": create_shipwright_foundry_mesh(),
            "FleetForge": create_fleet_forge_mesh(),
            "ResearchNexus": create_research_nexus_mesh(),
            "DefenseGridNode": create_defense_grid_node_mesh(),
        }
        self._facility_offsets: Dict[str, Tuple[float, float]] = {
            "ShipwrightFoundry": (-150.0, -70.0),
            "FleetForge": (150.0, -70.0),
            "ResearchNexus": (-150.0, 80.0),
            "DefenseGridNode": (150.0, 80.0),
        }
        self._facility_scales: Dict[str, float] = {
            "ShipwrightFoundry": 0.85,
            "FleetForge": 0.9,
            "ResearchNexus": 0.75,
            "DefenseGridNode": 0.78,
        }
        self.selection_color: Tuple[float, float, float, float] = (1.0, 0.82, 0.26, 1.0)
        self.enemy_color: Tuple[float, float, float, float] = (1.0, 0.35, 0.35, 1.0)
        self._fog_hidden_color: Tuple[float, float, float, float] = (0.02, 0.04, 0.07, 0.55)
        self._fog_unexplored_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.82)
        self._friendly_beam_color: Tuple[float, float, float] = (0.45, 0.88, 1.0)
        self._enemy_beam_color: Tuple[float, float, float] = (1.0, 0.45, 0.45)
        self._overlay_font = pygame.font.SysFont("Consolas", 16)
        self._spawn_button_rect: Optional[pygame.Rect] = None
        self._spawn_menu_rect: Optional[pygame.Rect] = None
        self._spawn_menu_buttons: List[ShipBuildButton] = []
        self._spawn_menu_visible: bool = False
        self._spawn_menu_base: Optional[Base] = None
        self._tooltip_padding = 8
        self._spawn_button_bg = (0.08, 0.11, 0.16, 0.92)
        self._spawn_button_hover = (0.16, 0.22, 0.32, 0.95)
        self._spawn_button_border = (0.32, 0.45, 0.65, 1.0)
        self._menu_bg = (0.05, 0.07, 0.11, 0.92)
        self._menu_border = (0.3, 0.38, 0.55, 1.0)
        self._menu_button_bg = (0.1, 0.13, 0.2, 0.95)
        self._menu_button_disabled = (0.06, 0.07, 0.09, 0.85)
        self._menu_button_border = (0.32, 0.4, 0.56, 1.0)
        self._menu_button_border_disabled = (0.18, 0.22, 0.3, 1.0)
        self._tooltip_bg = (0.08, 0.09, 0.12, 0.92)
        self._tooltip_border = (0.35, 0.42, 0.58, 1.0)
        self._current_viewport_size: Tuple[int, int] = (0, 0)

    def draw_world(
        self,
        world: World,
        camera: Camera3D,
        layout: UILayout,
        *,
        selection_box: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
    ) -> None:
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gameplay_rect = layout.gameplay_rect
        panel_height = layout.ui_panel_rect.height
        gl.glViewport(
            gameplay_rect.left,
            panel_height,
            gameplay_rect.width,
            gameplay_rect.height,
        )
        self._apply_camera(camera)

        for planetoid in world.planetoids:
            scale = planetoid.radius / 60.0
            self._draw_mesh(self.planetoid_mesh, planetoid.position, scale)

        for asteroid in world.asteroids:
            scale = asteroid.radius / 24.0
            self._draw_mesh(self.asteroid_mesh, asteroid.position, scale)

        for base in world.bases:
            self._draw_mesh(self.astral_citadel_mesh, base.position, 1.0)

        for facility in world.facilities:
            if not self._should_draw_facility(world, facility):
                continue
            mesh = self.facility_meshes.get(facility.facility_type)
            if mesh is None:
                continue
            position = self._facility_render_position(facility)
            scale = self._facility_scale(facility.facility_type)
            color = self._facility_color(world, facility)
            self._draw_mesh(mesh, position, scale, color=color, elevation=8.0)

        for ship in world.ships:
            if ship.faction != "player" and not world.visibility.is_visual(ship.position):
                continue
            mesh = self.ship_meshes.get(ship.definition.name)
            if mesh is None:
                # TODO: add visual fallback for ships without bespoke wireframes.
                continue
            scale = self._ship_scale_for(ship.definition.ship_class)
            color = LINE_COLOR
            if ship.faction != "player":
                color = self.enemy_color
            if ship in world.selected_ships:
                color = self.selection_color
            self._draw_mesh(mesh, ship.position, scale, color=color)

        self._draw_beam_visuals(world)

        self._draw_fog_overlay(world, camera)
        self._draw_gameplay_overlay(world, camera)

        if selection_box is not None:
            self._draw_screen_rect(selection_box[0], selection_box[1], camera.viewport_size)

    def _draw_mesh(
        self,
        mesh: WireframeMesh,
        position: Tuple[float, float],
        scale: float,
        *,
        color: Tuple[float, float, float, float] = LINE_COLOR,
        elevation: float = 0.0,
    ) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_LINES)
        for start_index, end_index in mesh.segments:
            sx, sy, sz = mesh.vertices[start_index]
            ex, ey, ez = mesh.vertices[end_index]

            start_world = (
                position[0] + sx * scale,
                elevation + sy * scale,
                position[1] + sz * scale,
            )
            end_world = (
                position[0] + ex * scale,
                elevation + ey * scale,
                position[1] + ez * scale,
            )

            gl.glVertex3f(*start_world)
            gl.glVertex3f(*end_world)
        gl.glEnd()

    @staticmethod
    def _compute_mesh_bounds(mesh: WireframeMesh) -> Tuple[float, float, float, float]:
        min_x = min((vertex[0] for vertex in mesh.vertices), default=-1.0)
        max_x = max((vertex[0] for vertex in mesh.vertices), default=1.0)
        min_z = min((vertex[2] for vertex in mesh.vertices), default=-1.0)
        max_z = max((vertex[2] for vertex in mesh.vertices), default=1.0)
        return (min_x, max_x, min_z, max_z)

    def _apply_camera(self, camera: Camera3D) -> None:
        projection = camera.projection_matrix()
        view = camera.view_matrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadMatrixf(np.transpose(projection).flatten())
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadMatrixf(np.transpose(view).flatten())

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
        if ship_class == "Utility":
            return 0.6
        return 1.0

    def _facility_scale(self, facility_type: str) -> float:
        return self._facility_scales.get(facility_type, 0.8)

    def _facility_render_position(self, facility: Facility) -> Tuple[float, float]:
        base = facility.host_base
        if base is not None:
            dx = facility.position[0] - base.position[0]
            dy = facility.position[1] - base.position[1]
            if abs(dx) < 1e-3 and abs(dy) < 1e-3:
                offset = self._facility_offsets.get(facility.facility_type, (0.0, 0.0))
                return (base.position[0] + offset[0], base.position[1] + offset[1])
        return facility.position

    def _facility_color(self, world: World, facility: Facility) -> Tuple[float, float, float, float]:
        base = facility.host_base
        faction = base.faction if base is not None else world.player_faction
        if faction != world.player_faction:
            return self.enemy_color
        if not facility.online:
            return (0.45, 0.5, 0.62, 1.0)
        return LINE_COLOR

    def _should_draw_facility(self, world: World, facility: Facility) -> bool:
        base = facility.host_base
        if base is not None and base.faction == world.player_faction:
            return True
        grid = getattr(world, "visibility", None)
        if grid is None:
            return True
        position = self._facility_render_position(facility)
        return grid.is_visual(position)

    def _draw_beam_visuals(self, world: World) -> None:
        beams = getattr(world, "beam_visuals", None)
        if not beams:
            return

        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glLineWidth(2.0)

        for beam in beams:
            alpha = getattr(beam, "alpha", None)
            alpha_value = alpha() if callable(alpha) else 1.0
            if alpha_value <= 0.0:
                continue
            color = self._beam_color_for_faction(getattr(beam, "faction", ""), alpha_value)
            start = getattr(beam, "start", (0.0, 0.0))
            end = getattr(beam, "end", (0.0, 0.0))
            self._draw_beam_segment(start, end, color)

        gl.glLineWidth(1.0)
        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)

    def _beam_color_for_faction(self, faction: str, alpha: float) -> Tuple[float, float, float, float]:
        base = self._friendly_beam_color if faction == "player" else self._enemy_beam_color
        glow = min(1.0, max(0.15, 0.25 + 0.75 * alpha))
        return (base[0], base[1], base[2], glow)

    @staticmethod
    def _draw_beam_segment(
        start: Tuple[float, float], end: Tuple[float, float], color: Tuple[float, float, float, float]
    ) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3f(start[0], 6.0, start[1])
        gl.glVertex3f(end[0], 6.0, end[1])
        gl.glEnd()

    def _draw_screen_rect(
        self,
        corner_a: Tuple[float, float],
        corner_b: Tuple[float, float],
        viewport_size: Tuple[int, int],
    ) -> None:
        min_x = min(corner_a[0], corner_b[0])
        max_x = max(corner_a[0], corner_b[0])
        min_y = min(corner_a[1], corner_b[1])
        max_y = max(corner_a[1], corner_b[1])

        width, height = viewport_size
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glOrtho(0, width, height, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glDisable(gl.GL_DEPTH_TEST)

        gl.glColor4f(*self.selection_color)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(min_x, min_y)
        gl.glVertex2f(max_x, min_y)
        gl.glVertex2f(max_x, max_y)
        gl.glVertex2f(min_x, max_y)
        gl.glEnd()

        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def _draw_gameplay_overlay(self, world: World, camera: Camera3D) -> None:
        overlay_active = self._begin_overlay(camera)
        if not overlay_active:
            return
        try:
            self._draw_base_progress_bars(world, camera)
            self._draw_selected_base_spawn_ui(world, camera)
        finally:
            self._end_overlay()

    def _begin_overlay(self, camera: Camera3D) -> bool:
        width, height = camera.viewport_size
        if width <= 0 or height <= 0:
            return False
        self._current_viewport_size = (width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glOrtho(0, width, height, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        return True

    def _end_overlay(self) -> None:
        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def _draw_base_progress_bars(self, world: World, camera: Camera3D) -> None:
        for base in world.bases:
            if base.faction != world.player_faction:
                continue
            job = base.production.active_job
            if job is None:
                continue
            screen_pos = camera.world_to_screen(base.position)
            if screen_pos is None:
                continue
            self._draw_progress_bar(screen_pos, job)

    def _draw_progress_bar(self, screen_pos: Tuple[float, float], job) -> None:
        definition = job.ship_definition
        total_time = max(0.1, definition.build_time)
        progress = 1.0 - max(0.0, job.remaining_time) / total_time
        width = 130
        height = 10
        bar_offset = 70
        rect = pygame.Rect(
            int(screen_pos[0] - width / 2),
            int(screen_pos[1] - bar_offset - height),
            width,
            height,
        )
        viewport_rect = pygame.Rect(0, 0, *self._current_viewport_size)
        if viewport_rect.width > 0 and viewport_rect.height > 0:
            if viewport_rect.width > 16 and viewport_rect.height > 16:
                rect.clamp_ip(viewport_rect.inflate(-8, -8))
            else:
                rect.clamp_ip(viewport_rect)
        self._draw_overlay_rect(rect, (0.04, 0.05, 0.08, 0.9))
        self._draw_overlay_outline(rect, (0.3, 0.38, 0.52, 1.0))
        inner = rect.inflate(-4, -4)
        fill_width = int(inner.width * progress)
        if fill_width > 0:
            fill = pygame.Rect(inner.left, inner.top, fill_width, inner.height)
            self._draw_overlay_rect(fill, (0.2, 0.6, 1.0, 0.95))
        label = f"{definition.name}"
        label_width, _ = self._overlay_font.size(label)
        text_x = rect.centerx - label_width / 2
        text_y = rect.top - 16
        if text_y < 0:
            text_y = rect.bottom + 4
        self._draw_overlay_text(text_x, text_y, label, (220, 230, 255))

    def _draw_selected_base_spawn_ui(self, world: World, camera: Camera3D) -> None:
        base = world.selected_base
        if base is None or base.faction != world.player_faction:
            self._spawn_button_rect = None
            self._spawn_menu_rect = None
            self._spawn_menu_buttons = []
            self._spawn_menu_visible = False
            self._spawn_menu_base = None
            return
        if self._spawn_menu_base is not None and self._spawn_menu_base is not base:
            self._close_spawn_menu()
        screen_pos = camera.world_to_screen(base.position)
        if screen_pos is None:
            self._spawn_button_rect = None
            return
        button_width = 160
        button_height = 32
        button_rect = pygame.Rect(
            int(screen_pos[0] - button_width / 2),
            int(screen_pos[1] - 36 - button_height),
            button_width,
            button_height,
        )
        self._spawn_button_rect = button_rect
        hovered = button_rect.collidepoint(pygame.mouse.get_pos())
        bg = self._spawn_button_hover if hovered else self._spawn_button_bg
        self._draw_overlay_rect(button_rect, bg)
        self._draw_overlay_outline(button_rect, self._spawn_button_border)
        label = "Spawn Ships"
        width, _ = self._overlay_font.size(label)
        text_x = button_rect.centerx - width / 2
        text_y = button_rect.centery - 8
        self._draw_overlay_text(text_x, text_y, label, (220, 235, 255))
        if not self._spawn_menu_visible or self._spawn_menu_base is not base:
            return
        self._draw_spawn_menu(world, base, button_rect)

    def _draw_spawn_menu(self, world: World, base: Base, anchor_rect: pygame.Rect) -> None:
        ship_defs = sorted(
            world.unlocked_ship_definitions(),
            key=lambda definition: (self._ship_class_order(definition.ship_class), definition.resource_cost),
        )
        columns = 4
        button_size = 72
        padding = 12
        rows = max(1, int(math.ceil(len(ship_defs) / columns))) if ship_defs else 1
        menu_width = columns * button_size + (columns + 1) * padding
        menu_height = rows * button_size + (rows + 1) * padding
        menu_x = anchor_rect.centerx - menu_width / 2
        menu_y = anchor_rect.top - menu_height - 18
        viewport_width = max(1, self._current_viewport_size[0])
        max_x = max(8, viewport_width - menu_width - 8)
        menu_x = max(8, min(menu_x, max_x))
        menu_y = max(8, menu_y)
        menu_rect = pygame.Rect(int(menu_x), int(menu_y), menu_width, menu_height)
        self._spawn_menu_rect = menu_rect
        self._draw_overlay_rect(menu_rect, self._menu_bg)
        self._draw_overlay_outline(menu_rect, self._menu_border)
        self._spawn_menu_buttons = []
        start_x = menu_rect.left + padding
        start_y = menu_rect.top + padding
        mouse_pos = pygame.mouse.get_pos()
        hovered_button: Optional[ShipBuildButton] = None
        if not ship_defs:
            self._draw_overlay_text(
                menu_rect.left + padding,
                menu_rect.top + padding,
                "No hulls unlocked yet",
                (200, 205, 220),
            )
            return
        for index, definition in enumerate(ship_defs):
            row = index // columns
            col = index % columns
            x = start_x + col * (button_size + padding)
            y = start_y + row * (button_size + padding)
            rect = pygame.Rect(int(x), int(y), button_size, button_size)
            allowed, _ = world.ship_production_status(base, definition)
            bg = self._menu_button_bg if allowed else self._menu_button_disabled
            border = self._menu_button_border if allowed else self._menu_button_border_disabled
            if rect.collidepoint(mouse_pos):
                hovered_button = ShipBuildButton(definition, rect, allowed)
            self._draw_overlay_rect(rect, bg)
            self._draw_overlay_outline(rect, border)
            self._draw_ship_icon(rect, definition, enabled=allowed)
            self._spawn_menu_buttons.append(ShipBuildButton(definition, rect, allowed))
        if hovered_button is not None:
            self._draw_ship_tooltip(mouse_pos, hovered_button)

    def _draw_ship_icon(
        self, rect: pygame.Rect, definition: ShipDefinition, *, enabled: bool
    ) -> None:
        mesh = self.ship_meshes.get(definition.name)
        if mesh is None:
            return
        bounds = self._ship_mesh_bounds.get(definition.name, (-1.0, 1.0, -1.0, 1.0))
        min_x, max_x, min_z, max_z = bounds
        span_x = max_x - min_x
        span_z = max_z - min_z
        available = rect.width - 16
        scale_x = available / span_x if span_x > 0 else available
        scale_z = available / span_z if span_z > 0 else available
        scale = min(scale_x, scale_z) * 0.9
        center_x = (max_x + min_x) * 0.5
        center_z = (max_z + min_z) * 0.5
        color = (1.0, 1.0, 1.0, 1.0) if enabled else (0.45, 0.5, 0.62, 1.0)
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_LINES)
        for start_index, end_index in mesh.segments:
            sx, _, sz = mesh.vertices[start_index]
            ex, _, ez = mesh.vertices[end_index]
            start_x = rect.centerx + (sx - center_x) * scale
            start_y = rect.centery - (sz - center_z) * scale
            end_x = rect.centerx + (ex - center_x) * scale
            end_y = rect.centery - (ez - center_z) * scale
            gl.glVertex2f(start_x, start_y)
            gl.glVertex2f(end_x, end_y)
        gl.glEnd()

    def _draw_ship_tooltip(self, mouse_pos: Tuple[int, int], button: ShipBuildButton) -> None:
        lines = [
            button.definition.name,
            f"Cost: {button.definition.resource_cost:,}",
            f"Build time: {button.definition.build_time:.0f}s",
        ]
        widths = [self._overlay_font.size(line)[0] for line in lines]
        tooltip_width = max(widths) + self._tooltip_padding * 2
        tooltip_height = len(lines) * 18 + self._tooltip_padding * 2
        x = mouse_pos[0] + 18
        y = mouse_pos[1] - tooltip_height - 18
        if y < 8:
            y = mouse_pos[1] + 18
        rect = pygame.Rect(int(x), int(y), tooltip_width, tooltip_height)
        self._draw_overlay_rect(rect, self._tooltip_bg)
        self._draw_overlay_outline(rect, self._tooltip_border)
        text_y = rect.top + self._tooltip_padding
        for line in lines:
            self._draw_overlay_text(rect.left + self._tooltip_padding, text_y, line, (230, 235, 255))
            text_y += 18

    def _draw_overlay_rect(self, rect: pygame.Rect, color: Tuple[float, float, float, float]) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(rect.left, rect.top)
        gl.glVertex2f(rect.right, rect.top)
        gl.glVertex2f(rect.right, rect.bottom)
        gl.glVertex2f(rect.left, rect.bottom)
        gl.glEnd()

    def _draw_overlay_outline(self, rect: pygame.Rect, color: Tuple[float, float, float, float]) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(rect.left, rect.top)
        gl.glVertex2f(rect.right, rect.top)
        gl.glVertex2f(rect.right, rect.bottom)
        gl.glVertex2f(rect.left, rect.bottom)
        gl.glEnd()

    def _draw_overlay_text(self, x: float, y: float, text: str, color: Tuple[int, int, int]) -> None:
        surface = self._overlay_font.render(text, True, color)
        data = pygame.image.tostring(surface, "RGBA", True)
        gl.glRasterPos2f(x, y)
        gl.glDrawPixels(
            surface.get_width(),
            surface.get_height(),
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            data,
        )

    def handle_spawn_ui_click(self, world: World, pos: Tuple[int, int]) -> bool:
        base = world.selected_base
        if base is None or base.faction != world.player_faction:
            self._close_spawn_menu()
            return False
        if self._spawn_button_rect and self._spawn_button_rect.collidepoint(pos):
            if not self._spawn_menu_visible or self._spawn_menu_base is not base:
                self._spawn_menu_visible = True
                self._spawn_menu_base = base
            else:
                self._close_spawn_menu()
            return True
        if not self._spawn_menu_visible or self._spawn_menu_base is not base:
            return False
        for button in self._spawn_menu_buttons:
            if not button.rect.collidepoint(pos):
                continue
            if button.enabled:
                world.queue_ship(base, button.definition.name)
            return True
        if self._spawn_menu_rect and self._spawn_menu_rect.collidepoint(pos):
            return True
        self._close_spawn_menu()
        return True

    def _close_spawn_menu(self) -> None:
        self._spawn_menu_visible = False
        self._spawn_menu_base = None
        self._spawn_menu_buttons = []
        self._spawn_menu_rect = None

    @staticmethod
    def _ship_class_order(ship_class: str) -> int:
        order = {"Strike": 0, "Escort": 1, "Line": 2, "Capital": 3}
        return order.get(ship_class, 99)

    def _draw_fog_overlay(self, world: World, camera: Camera3D) -> None:
        grid = getattr(world, "visibility", None)
        if grid is None:
            return
        viewport_w, viewport_h = camera.viewport_size
        if viewport_w <= 0 or viewport_h <= 0:
            return

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glOrtho(0, viewport_w, viewport_h, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        for row, col, cell in grid.cells():
            if not cell.explored:
                color = self._fog_unexplored_color
            elif not cell.visual:
                color = self._fog_hidden_color
            else:
                continue
            min_x, max_x, min_y, max_y = grid.cell_bounds(row, col)
            corners = (
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y),
            )
            projected = []
            for world_pos in corners:
                screen = camera.world_to_screen(world_pos)
                if screen is None:
                    break
                projected.append(screen)
            if len(projected) != 4:
                # TODO: Handle partially visible cells by clipping polygon to viewport.
                continue
            gl.glColor4f(*color)
            gl.glBegin(gl.GL_QUADS)
            for x, y in projected:
                gl.glVertex2f(x, y)
            gl.glEnd()

        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)
