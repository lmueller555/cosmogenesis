"""Renderer for the Cosmogenesis bottom HUD panel."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import math
import pygame
from OpenGL import GL as gl

from game.camera import Camera3D
from game.entities import Base, Ship
from game.research import ResearchAvailability, ResearchNode
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
        self._enemy_radar_color = (1.0, 0.4, 0.4, 0.65)
        self._minimap_bg = (0.02, 0.02, 0.03, 1.0)
        self._fog_unexplored = (0.0, 0.0, 0.0, 0.8)
        self._fog_hidden = (0.03, 0.03, 0.05, 0.55)
        self._planetoid_colors = {
            "player": (0.3, 0.8, 1.0, 0.9),
            "enemy": (1.0, 0.35, 0.35, 0.9),
            "neutral": (0.7, 0.7, 0.7, 0.85),
        }
        self._asteroid_colors = {
            "player": (0.35, 0.75, 0.95, 0.75),
            "enemy": (1.0, 0.4, 0.4, 0.75),
            "neutral": (0.6, 0.6, 0.6, 0.7),
        }
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
        income_suffix = ""
        if world.resource_income_rate > 0.0:
            income_suffix = f" (+{world.resource_income_rate:.1f}/s)"
        self._draw_text(
            cursor_x,
            cursor_y,
            f"Resources: {world.resources:.0f}{income_suffix}",
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

        availabilities: List[ResearchAvailability] = world.research_statuses()
        if not availabilities:
            idle_message = (
                "All projects complete." if progress_snapshot is None else "Research in progress."
            )
            self._draw_text(cursor_x, cursor_y, idle_message, self._muted_text)
            cursor_y += 22
            return cursor_y

        ready = [entry for entry in availabilities if entry.can_start]
        locked = [entry for entry in availabilities if not entry.can_start]

        if ready:
            self._draw_text(cursor_x, cursor_y, "Available Projects", self._context_text)
            cursor_y += 24
            for entry in ready:
                height = 88
                button_rect = pygame.Rect(rect.left + 8, int(cursor_y), rect.width - 16, height)
                self._draw_research_button(
                    button_rect,
                    entry.node,
                    enabled=True,
                    status_line="Ready to start",
                )
                self._research_buttons.append(
                    ResearchButton(node_id=entry.node.id, rect=button_rect, enabled=True)
                )
                cursor_y += height + 8
        else:
            idle_message = (
                "Research in progress." if progress_snapshot is not None else "No projects can start yet."
            )
            self._draw_text(cursor_x, cursor_y, idle_message, self._muted_text)
            cursor_y += 22

        if locked:
            cursor_y += 12
            self._draw_text(cursor_x, cursor_y, "Locked Projects", self._context_text)
            cursor_y += 24
            for entry in locked:
                height = 88
                button_rect = pygame.Rect(rect.left + 8, int(cursor_y), rect.width - 16, height)
                status_line = entry.blocked_reason or "Unavailable"
                self._draw_research_button(
                    button_rect,
                    entry.node,
                    enabled=False,
                    status_line=status_line,
                )
                self._research_buttons.append(
                    ResearchButton(
                        node_id=entry.node.id,
                        rect=button_rect,
                        enabled=False,
                    )
                )
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
            height = 72
            button_rect = pygame.Rect(rect.left + 8, int(cursor_y), rect.width - 16, height)
            enabled, status_line = self._ship_button_state(world, base, definition)
            self._draw_ship_button(button_rect, definition, enabled, status_line=status_line)
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

        self._draw_fog_overlay(world, rect, bounds)

        for planetoid in world.planetoids:
            center = self._world_to_minimap(planetoid.position, rect, bounds)
            radius = self._planetoid_radius(planetoid.radius, rect, bounds)
            color = self._planetoid_color(planetoid.controller)
            self._draw_minimap_planetoid(center, radius, color)

        for asteroid in world.asteroids:
            center = self._world_to_minimap(asteroid.position, rect, bounds)
            radius = self._asteroid_radius(asteroid.radius, rect, bounds)
            color = self._asteroid_color(asteroid.controller)
            self._draw_minimap_asteroid(center, radius, color)

        for ship in world.ships:
            color = self._friendly_color
            if ship.faction != "player":
                if not world.visibility.is_radar(ship.position):
                    continue
                if world.visibility.is_visual(ship.position):
                    color = self._enemy_color
                else:
                    color = self._enemy_radar_color
            else:
                if ship in world.selected_ships:
                    color = self._selected_color
            point = self._world_to_minimap(ship.position, rect, bounds)
            self._draw_minimap_dot(point, color)

        for base in world.bases:
            point = self._world_to_minimap(base.position, rect, bounds)
            self._draw_minimap_dot(point, self._friendly_color, size=5.0)

        self._draw_camera_outline(camera, rect, bounds)
        self._draw_minimap_outline(rect)

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

    def _draw_minimap_outline(self, rect: pygame.Rect) -> None:
        gl.glColor4f(0.4, 0.45, 0.6, 1.0)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(rect.left, rect.top)
        gl.glVertex2f(rect.right, rect.top)
        gl.glVertex2f(rect.right, rect.bottom)
        gl.glVertex2f(rect.left, rect.bottom)
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

    def _draw_fog_overlay(
        self, world: World, rect: pygame.Rect, bounds: Tuple[float, float, float, float]
    ) -> None:
        grid = getattr(world, "visibility", None)
        if grid is None:
            return
        world_width = bounds[1] - bounds[0]
        world_height = bounds[3] - bounds[2]
        if world_width <= 0 or world_height <= 0:
            return
        for row, col, cell in grid.cells():
            if not cell.explored:
                color = self._fog_unexplored
            elif not cell.visual:
                color = self._fog_hidden
            else:
                continue
            min_x, max_x, min_y, max_y = grid.cell_bounds(row, col)
            left = rect.left + ((min_x - bounds[0]) / world_width) * rect.width
            right = rect.left + ((max_x - bounds[0]) / world_width) * rect.width
            bottom = rect.bottom - ((min_y - bounds[2]) / world_height) * rect.height
            top = rect.bottom - ((max_y - bounds[2]) / world_height) * rect.height
            self._draw_minimap_quad(left, right, top, bottom, color)

    def _draw_minimap_quad(
        self,
        left: float,
        right: float,
        top: float,
        bottom: float,
        color: Tuple[float, float, float, float],
    ) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(left, top)
        gl.glVertex2f(right, top)
        gl.glVertex2f(right, bottom)
        gl.glVertex2f(left, bottom)
        gl.glEnd()

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

    def _planetoid_color(self, controller: str) -> Tuple[float, float, float, float]:
        if controller == "player":
            return self._planetoid_colors["player"]
        if controller == "enemy":
            return self._planetoid_colors["enemy"]
        return self._planetoid_colors["neutral"]

    def _asteroid_color(self, controller: str) -> Tuple[float, float, float, float]:
        if controller == "player":
            return self._asteroid_colors["player"]
        if controller == "enemy":
            return self._asteroid_colors["enemy"]
        return self._asteroid_colors["neutral"]

    def _planetoid_radius(
        self, world_radius: float, rect: pygame.Rect, bounds: Tuple[float, float, float, float]
    ) -> float:
        min_x, max_x, min_y, max_y = bounds
        world_width = max_x - min_x
        world_height = max_y - min_y
        if world_width <= 0 or world_height <= 0:
            return 4.0
        radius_x = (world_radius / world_width) * rect.width
        radius_y = (world_radius / world_height) * rect.height
        radius = max(3.0, min(radius_x, radius_y))
        return radius

    def _asteroid_radius(
        self, world_radius: float, rect: pygame.Rect, bounds: Tuple[float, float, float, float]
    ) -> float:
        return max(2.0, self._planetoid_radius(world_radius, rect, bounds) * 0.45)

    def _draw_minimap_planetoid(
        self,
        center: Vec2,
        radius: float,
        color: Tuple[float, float, float, float],
        segments: int = 20,
    ) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glVertex2f(center[0], center[1])
        for i in range(segments + 1):
            angle = (i / segments) * 2.0 * 3.14159265
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            gl.glVertex2f(x, y)
        gl.glEnd()

    def _draw_minimap_asteroid(
        self,
        center: Vec2,
        radius: float,
        color: Tuple[float, float, float, float],
        segments: int = 10,
    ) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(segments):
            angle = (i / segments) * 2.0 * 3.14159265
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            gl.glVertex2f(x, y)
        gl.glEnd()

    def _draw_research_button(
        self,
        rect: pygame.Rect,
        node: ResearchNode,
        *,
        enabled: bool,
        status_line: str | None = None,
    ) -> None:
        if enabled:
            bg = (0.10, 0.14, 0.21, 0.95)
            border = (0.32, 0.45, 0.65, 1.0)
            title_color = self._text_color
            detail_color = self._context_text
        else:
            bg = (0.07, 0.09, 0.12, 0.8)
            border = (0.18, 0.22, 0.30, 1.0)
            title_color = self._muted_text
            detail_color = self._muted_text
        self._draw_rect(rect, bg)
        self._draw_rect_outline(rect, border)

        text_x = rect.left + 10
        text_y = rect.top + 12
        name_line = f"{node.name} (Tier {node.tier})"
        cost_line = f"Cost {node.resource_cost:,} | {node.research_time:.0f}s"
        detail_line = self._node_detail_line(node)

        self._draw_text(text_x, text_y, name_line, title_color)
        self._draw_text(text_x, text_y + 20, cost_line, self._muted_text)
        self._draw_text(text_x, text_y + 40, detail_line, detail_color)
        if status_line:
            line_color = detail_color if not enabled else self._context_text
            self._draw_text(text_x, text_y + 60, status_line, line_color)

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

    def _ship_button_state(
        self, world: World, base: Optional[Base], definition: ShipDefinition
    ) -> Tuple[bool, Optional[str]]:
        if base is None:
            return False, "No operational base"
        allowed, reason = world.ship_production_status(base, definition)
        return allowed, reason

    def _draw_ship_button(
        self,
        rect: pygame.Rect,
        definition: ShipDefinition,
        enabled: bool,
        *,
        status_line: Optional[str] = None,
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
        if status_line:
            status_color = self._muted_text if not enabled else self._context_text
            self._draw_text(text_x, text_y + 52, status_line, status_color)

    @staticmethod
    def _ship_class_order(ship_class: str) -> int:
        order = {"Strike": 0, "Escort": 1, "Line": 2, "Capital": 3}
        return order.get(ship_class, 99)

