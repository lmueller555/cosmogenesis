"""Renderer for the Cosmogenesis bottom HUD panel."""
from __future__ import annotations

from typing import Iterable, List, Tuple

import pygame
from OpenGL import GL as gl

from game.camera import Camera3D
from game.entities import Ship
from game.world import World
from .layout import UILayout


Vec2 = Tuple[float, float]


class UIPanelRenderer:
    """Draws the mini-map, selection summary, and context panel."""

    def __init__(self) -> None:
        pygame.font.init()
        self._font = pygame.font.SysFont("Consolas", 18)
        self._bg_color = (0.04, 0.05, 0.08, 0.95)
        self._panel_border = (0.35, 0.42, 0.55, 1.0)
        self._text_color = (230, 235, 255)
        self._muted_text = (160, 170, 190)
        self._context_text = (200, 210, 230)
        self._friendly_color = (1.0, 1.0, 1.0, 1.0)
        self._selected_color = (0.2, 0.6, 1.0, 1.0)
        self._enemy_color = (1.0, 0.25, 0.25, 1.0)
        self._minimap_bg = (0.02, 0.02, 0.03, 1.0)

    def draw(self, world: World, camera: Camera3D, layout: UILayout) -> None:
        width, height = layout.window_size
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, width, height, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glDisable(gl.GL_DEPTH_TEST)

        self._draw_panel_background(layout)
        self._draw_selection_summary(world.selected_ships, layout.selection_rect)
        self._draw_context_panel(world, layout.context_rect)
        self._draw_minimap(world, camera, layout.minimap_rect)

        gl.glEnable(gl.GL_DEPTH_TEST)

    # ------------------------------------------------------------------
    # Background & panel scaffolding
    # ------------------------------------------------------------------
    def _draw_panel_background(self, layout: UILayout) -> None:
        rect = layout.ui_panel_rect
        self._draw_rect(rect, self._bg_color)
        self._draw_rect_outline(rect, self._panel_border)

        selection = layout.selection_rect
        self._draw_rect_outline(selection, (0.15, 0.18, 0.25, 1.0))

        context = layout.context_rect
        self._draw_rect_outline(context, (0.15, 0.18, 0.25, 1.0))

    def _draw_rect(self, rect: pygame.Rect, color: Tuple[float, float, float, float]) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(rect.left, rect.top)
        gl.glVertex2f(rect.right, rect.top)
        gl.glVertex2f(rect.right, rect.bottom)
        gl.glVertex2f(rect.left, rect.bottom)
        gl.glEnd()

    def _draw_rect_outline(
        self, rect: pygame.Rect, color: Tuple[float, float, float, float]
    ) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(rect.left, rect.top)
        gl.glVertex2f(rect.right, rect.top)
        gl.glVertex2f(rect.right, rect.bottom)
        gl.glVertex2f(rect.left, rect.bottom)
        gl.glEnd()

    # ------------------------------------------------------------------
    # Selection summary
    # ------------------------------------------------------------------
    def _draw_selection_summary(self, selection: Iterable[Ship], rect: pygame.Rect) -> None:
        ships = list(selection)
        if not ships:
            self._draw_text_block(
                rect.left + 16,
                rect.top + 24,
                ["No units selected", "Left-click a ship or drag a selection box."],
                color=self._muted_text,
            )
            return

        focus = ships[0]
        lines = [
            f"{focus.name} ({focus.ship_class})",
            f"HP: {focus.current_health:.0f}/{focus.max_health:.0f}",
            f"Armor: {focus.armor_value:.0f}",
            f"Shields: {focus.current_shields:.0f}/{focus.max_shields:.0f}",
            f"Energy: {focus.current_energy:.0f}/{focus.max_energy:.0f} (+{focus.energy_regen_value:.1f}/s)",
            f"Weapon Damage: {focus.weapon_damage_value:.0f}",
            f"Flight Speed: {focus.flight_speed:.0f}",
            f"Visual Range: {focus.visual_range:.0f}",
            f"Radar Range: {focus.radar_range:.0f}",
            f"Firing Range: {focus.firing_range:.0f}",
        ]
        if len(ships) > 1:
            lines.insert(1, f"Group size: {len(ships)} ships")
        self._draw_text_block(rect.left + 16, rect.top + 24, lines)

    def _draw_text_block(
        self,
        x: float,
        y: float,
        lines: List[str],
        *,
        color: Tuple[int, int, int] | None = None,
    ) -> None:
        current_y = y
        for line in lines:
            self._draw_text(x, current_y, line, color or self._text_color)
            current_y += 22

    def _draw_text(self, x: float, y: float, text: str, color: Tuple[int, int, int]) -> None:
        surface = self._font.render(text, True, color)
        data = pygame.image.tostring(surface, "RGBA", True)
        gl.glRasterPos2f(x, y)
        gl.glDrawPixels(
            surface.get_width(),
            surface.get_height(),
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            data,
        )

    # ------------------------------------------------------------------
    # Context panel placeholder
    # ------------------------------------------------------------------
    def _draw_context_panel(self, world: World, rect: pygame.Rect) -> None:
        lines = [
            "Context / Actions",
            "------------------",
            "TODO: Populate with build",
            "options, research buttons,",
            "and abilities per ui_guidance.",
        ]
        self._draw_text_block(rect.left + 12, rect.top + 24, lines, color=self._context_text)

    # ------------------------------------------------------------------
    # Mini-map
    # ------------------------------------------------------------------
    def _draw_minimap(self, world: World, camera: Camera3D, rect: pygame.Rect) -> None:
        self._draw_rect(rect, self._minimap_bg)
        self._draw_rect_outline(rect, (0.4, 0.45, 0.6, 1.0))

        bounds = self._world_bounds(world)

        # TODO: Integrate fog-of-war exploration state rather than showing everything.
        for ship in world.ships:
            color = self._friendly_color if ship.faction == "player" else self._enemy_color
            if ship in world.selected_ships and ship.faction == "player":
                color = self._selected_color
            point = self._world_to_minimap(ship.position, rect, bounds)
            self._draw_minimap_dot(point, color)

        for base in world.bases:
            point = self._world_to_minimap(base.position, rect, bounds)
            self._draw_minimap_dot(point, self._friendly_color, size=5.0)

        self._draw_camera_outline(camera, rect, bounds)

    def _draw_camera_outline(
        self, camera: Camera3D, minimap_rect: pygame.Rect, bounds: Tuple[float, float, float, float]
    ) -> None:
        viewport_w, viewport_h = camera.viewport_size
        if viewport_w <= 0 or viewport_h <= 0:
            return
        corners = [
            (0.0, 0.0),
            (float(viewport_w), 0.0),
            (float(viewport_w), float(viewport_h)),
            (0.0, float(viewport_h)),
        ]
        world_points: List[Vec2] = []
        for corner in corners:
            world_points.append(camera.screen_to_world(corner))

        map_points = [self._world_to_minimap(p, minimap_rect, bounds) for p in world_points]
        gl.glColor4f(1.0, 1.0, 1.0, 1.0)
        gl.glBegin(gl.GL_LINE_LOOP)
        for x, y in map_points:
            gl.glVertex2f(x, y)
        gl.glEnd()

    def _draw_minimap_dot(
        self, point: Vec2, color: Tuple[float, float, float, float], size: float = 4.0
    ) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(point[0] - size * 0.5, point[1] - size * 0.5)
        gl.glVertex2f(point[0] + size * 0.5, point[1] - size * 0.5)
        gl.glVertex2f(point[0] + size * 0.5, point[1] + size * 0.5)
        gl.glVertex2f(point[0] - size * 0.5, point[1] + size * 0.5)
        gl.glEnd()

    def _world_bounds(self, world: World) -> Tuple[float, float, float, float]:
        half_w = world.width * 0.5
        half_h = world.height * 0.5
        return (-half_w, half_w, -half_h, half_h)

    def _world_to_minimap(
        self,
        position: Vec2,
        rect: pygame.Rect,
        bounds: Tuple[float, float, float, float],
    ) -> Vec2:
        min_x, max_x, min_y, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        if width <= 0 or height <= 0:
            return (rect.centerx, rect.centery)
        normalized_x = (position[0] - min_x) / width
        normalized_y = (position[1] - min_y) / height
        x = rect.left + normalized_x * rect.width
        y = rect.bottom - normalized_y * rect.height
        return (x, y)

