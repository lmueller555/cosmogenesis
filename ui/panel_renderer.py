"""Renderer for the Cosmogenesis bottom HUD panel."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

import pygame
from OpenGL import GL as gl

from game.camera import Camera3D
from game.entities import Ship
from game.research import ResearchNode
from game.world import World
from game.ship_registry import ShipDefinition
from .layout import UILayout


Vec2 = Tuple[float, float]


@dataclass
class ResearchButton:
    node_id: str
    rect: pygame.Rect
    enabled: bool = True


@dataclass
class ProductionButton:
    ship_name: str
    rect: pygame.Rect
    enabled: bool = True


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
        self._research_buttons: List[ResearchButton] = []
        self._production_buttons: List[ProductionButton] = []

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

    def handle_mouse_click(self, world: World, layout: UILayout, pos: Vec2) -> bool:
        """Process left-clicks in the context panel.

        Returns ``True`` if the event was handled (preventing other UI uses).
        """

        if not layout.context_rect.collidepoint(pos):
            return False
        for button in self._research_buttons:
            if not button.enabled:
                continue
            if button.rect.collidepoint(pos):
                if world.try_start_research(button.node_id):
                    return True
        base = world.player_primary_base()
        for button in self._production_buttons:
            if not button.rect.collidepoint(pos):
                continue
            if base is None:
                return True
            if button.enabled and world.queue_ship(base, button.ship_name):
                return True
            return True
        return True  # Click in panel but nothing actionable

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
        padding = 12
        cursor_x = rect.left + padding
        cursor_y = rect.top + padding
        self._research_buttons.clear()
        self._production_buttons.clear()

        self._draw_text(cursor_x, cursor_y, "Research Console", self._context_text)
        cursor_y += 26
        self._draw_text(
            cursor_x,
            cursor_y,
            f"Resources: {world.resources:.0f}",
            self._muted_text,
        )
        cursor_y += 24

        cursor_y = self._draw_research_section(world, rect, cursor_x, cursor_y)
        cursor_y += 18
        self._draw_construction_section(world, rect, cursor_x, cursor_y)

    def _draw_research_section(
        self, world: World, rect: pygame.Rect, cursor_x: float, cursor_y: float
    ) -> float:
        progress_snapshot = world.research_manager.active_progress()
        if progress_snapshot is None:
            self._draw_text(cursor_x, cursor_y, "No active research", self._muted_text)
            cursor_y += 26
        else:
            node = progress_snapshot.node
            self._draw_text(cursor_x, cursor_y, f"Active: {node.name}", self._text_color)
            cursor_y += 22
            percent = progress_snapshot.progress_fraction * 100.0
            time_left = progress_snapshot.remaining_time
            paused_suffix = " (paused)" if progress_snapshot.paused else ""
            progress_line = f"{percent:4.0f}% complete  ({time_left:0.1f}s left){paused_suffix}"
            self._draw_text(cursor_x, cursor_y, progress_line, self._muted_text)
            cursor_y += 28

        available = sorted(
            world.available_research(), key=lambda node: (node.tier, node.name)
        )
        if not available:
            idle_message = (
                "Research in progress." if progress_snapshot is not None else "No projects available."
            )
            self._draw_text(cursor_x, cursor_y, idle_message, self._muted_text)
            cursor_y += 22
            self._draw_text(
                cursor_x,
                cursor_y,
                "Check facilities, prerequisites, or resources.",
                self._muted_text,
            )
            cursor_y += 32
            return cursor_y

        self._draw_text(cursor_x, cursor_y, "Available Projects", self._context_text)
        cursor_y += 24

        for node in available:
            height = 68
            button_rect = pygame.Rect(rect.left + 8, int(cursor_y), rect.width - 16, height)
            self._draw_research_button(button_rect, node)
            self._research_buttons.append(ResearchButton(node_id=node.id, rect=button_rect))
            cursor_y += height + 8
        return cursor_y

    def _draw_construction_section(
        self, world: World, rect: pygame.Rect, cursor_x: float, cursor_y: float
    ) -> None:
        self._draw_text(cursor_x, cursor_y, "Ship Construction", self._context_text)
        cursor_y += 24

        base = world.player_primary_base()
        if base is None:
            self._draw_text(cursor_x, cursor_y, "No operational base.", self._muted_text)
            cursor_y += 22
            self._draw_text(cursor_x, cursor_y, "Build a base to produce ships.", self._muted_text)
            return

        active_job = base.production.active_job
        if active_job is None:
            self._draw_text(cursor_x, cursor_y, "Idle shipyards", self._muted_text)
            cursor_y += 22
        else:
            definition = active_job.ship_definition
            total_time = max(0.1, definition.build_time)
            progress = 1.0 - (active_job.remaining_time / total_time)
            self._draw_text(
                cursor_x,
                cursor_y,
                f"Building: {definition.name} ({progress * 100:4.0f}% complete)",
                self._text_color,
            )
            cursor_y += 20
            self._draw_text(
                cursor_x,
                cursor_y,
                f"{active_job.remaining_time:0.1f}s remaining",
                self._muted_text,
            )
            cursor_y += 24

        queued = list(base.production.queued_jobs)
        if queued:
            queue_names = ", ".join(job.ship_definition.name for job in queued[:3])
            more = len(queued) - 3
            suffix = f" (+{more} more)" if more > 0 else ""
            self._draw_text(
                cursor_x,
                cursor_y,
                f"Queue: {queue_names}{suffix}",
                self._muted_text,
            )
            cursor_y += 26
        else:
            self._draw_text(cursor_x, cursor_y, "Queue empty", self._muted_text)
            cursor_y += 22

        ship_defs = sorted(
            world.unlocked_ship_definitions(),
            key=lambda definition: (self._ship_class_order(definition.ship_class), definition.resource_cost),
        )
        if not ship_defs:
            self._draw_text(cursor_x, cursor_y, "No hulls unlocked yet.", self._muted_text)
            return

        self._draw_text(cursor_x, cursor_y, "Available Hulls", self._context_text)
        cursor_y += 24

        for definition in ship_defs:
            height = 56
            button_rect = pygame.Rect(rect.left + 8, int(cursor_y), rect.width - 16, height)
            affordable = world.resources >= definition.resource_cost
            enabled = affordable
            self._draw_ship_button(button_rect, definition, enabled)
            self._production_buttons.append(
                ProductionButton(ship_name=definition.name, rect=button_rect, enabled=enabled)
            )
            cursor_y += height + 6

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

    def _draw_research_button(self, rect: pygame.Rect, node: ResearchNode) -> None:
        bg = (0.10, 0.14, 0.21, 0.95)
        border = (0.32, 0.45, 0.65, 1.0)
        self._draw_rect(rect, bg)
        self._draw_rect_outline(rect, border)

        text_x = rect.left + 10
        text_y = rect.top + 12
        name_line = f"{node.name} (Tier {node.tier})"
        cost_line = f"Cost {node.resource_cost:,} | {node.research_time:.0f}s"
        detail_line = self._node_detail_line(node)

        self._draw_text(text_x, text_y, name_line, self._text_color)
        self._draw_text(text_x, text_y + 20, cost_line, self._muted_text)
        self._draw_text(text_x, text_y + 40, detail_line, self._context_text)

    def _node_detail_line(self, node: ResearchNode) -> str:
        if node.unlocks_ships:
            ships = ", ".join(node.unlocks_ships)
            return self._truncate(f"Unlocks: {ships}")
        if node.stat_bonuses:
            return self._truncate(node.stat_bonuses[0].description)
        if node.description:
            return self._truncate(node.description)
        return ""

    @staticmethod
    def _truncate(text: str, max_chars: int = 60) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    def _draw_ship_button(
        self, rect: pygame.Rect, definition: ShipDefinition, enabled: bool
    ) -> None:
        if enabled:
            bg = (0.12, 0.16, 0.23, 0.95)
            text_color = self._text_color
        else:
            bg = (0.08, 0.08, 0.10, 0.8)
            text_color = self._muted_text
        border = (0.28, 0.35, 0.48, 1.0)
        self._draw_rect(rect, bg)
        self._draw_rect_outline(rect, border)
        text_x = rect.left + 10
        text_y = rect.top + 12
        self._draw_text(text_x, text_y, f"{definition.name} ({definition.ship_class})", text_color)
        self._draw_text(
            text_x,
            text_y + 20,
            f"{definition.role}",
            self._muted_text,
        )
        self._draw_text(
            text_x,
            text_y + 36,
            f"Cost {definition.resource_cost:,} | {definition.build_time:.0f}s",
            self._context_text,
        )

    @staticmethod
    def _ship_class_order(ship_class: str) -> int:
        order = {"Strike": 0, "Escort": 1, "Line": 2, "Capital": 3}
        return order.get(ship_class, 99)

