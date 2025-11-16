"""Renderer for the Cosmogenesis bottom HUD panel."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

import math
import pygame
from OpenGL import GL as gl

from game.camera import Camera3D
from game.entities import Base, Ship, Facility
from game.research import ResearchAvailability, ResearchNode
from game.world import World
from game.visibility import VisibilityGrid
from game.ship_registry import ShipDefinition
from game.facility_registry import FacilityDefinition, all_facility_definitions
from game.production import ProductionJob
from rendering.wireframe_primitives import (
    WireframeMesh,
    create_defense_grid_node_mesh,
    create_fleet_forge_mesh,
    create_research_nexus_mesh,
    create_shipwright_foundry_mesh,
)
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


@dataclass
class FacilityButton:
    facility_type: str
    rect: pygame.Rect
    enabled: bool = True
    context: str = "base"


@dataclass(frozen=True)
class FacilityIconMesh:
    vertices: List[Vec2]
    segments: Sequence[Tuple[int, int]]
    bounds: Tuple[float, float, float, float]


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
        self._ship_class_colors = {
            "Strike": (0.22, 0.42, 0.65, 0.92),
            "Escort": (0.25, 0.55, 0.45, 0.92),
            "Line": (0.55, 0.38, 0.25, 0.92),
            "Capital": (0.58, 0.32, 0.55, 0.92),
        }
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
        self._facility_icon_meshes = self._build_facility_icon_meshes()
        self._research_buttons: List[ResearchButton] = []
        self._production_buttons: List[ProductionButton] = []
        self._facility_buttons: List[FacilityButton] = []
        self._context_scroll: float = 0.0
        self._context_content_height: float = 0.0

    def draw(self, world: World, camera: Camera3D, layout: UILayout) -> None:
        self._research_buttons.clear()
        self._production_buttons.clear()
        self._facility_buttons.clear()

        width, height = layout.window_size
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, width, height, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self._draw_panel_background(layout)
        self._draw_selection_summary(world, layout.selection_rect)

        clip_rect = self._context_clip_rect(layout)

        def draw_context() -> None:
            content_height = self._draw_context_panel(
                world, layout.context_rect, self._context_scroll
            )
            self._update_context_scroll_bounds(layout.context_rect, content_height)

        if clip_rect is None:
            draw_context()
        else:
            self._with_scissor(clip_rect, layout.window_size, draw_context)

        self._draw_minimap(world, camera, layout.minimap_rect)

        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)

    def handle_mouse_click(self, world: World, layout: UILayout, pos: Vec2) -> bool:
        """Process left-clicks in the HUD panel."""

        if not layout.ui_panel_rect.collidepoint(pos):
            return False

        if layout.selection_rect.collidepoint(pos):
            if self._handle_selection_click(world, pos):
                return True

        if layout.context_rect.collidepoint(pos):
            return self._handle_context_click(world, pos)

        return True  # Click fell within the HUD but not on actionable widgets

    def _handle_selection_click(self, world: World, pos: Vec2) -> bool:
        base = world.selected_base
        if base is None:
            return True
        for button in self._production_buttons:
            if not button.enabled or not button.rect.collidepoint(pos):
                continue
            if world.queue_ship(base, button.ship_name):
                return True
            return True
        return True

    def _handle_context_click(self, world: World, pos: Vec2) -> bool:
        for button in self._research_buttons:
            if not button.enabled:
                continue
            if button.rect.collidepoint(pos):
                if world.try_start_research(button.node_id):
                    return True
        base = world.selected_base
        worker = self._primary_worker(world)
        for button in self._facility_buttons:
            if not button.rect.collidepoint(pos):
                continue
            if button.context == "worker":
                if worker is None:
                    return True
                if button.enabled:
                    world.start_worker_construction(worker, button.facility_type)
                return True
            if base is None:
                return True
            if button.enabled and world.queue_facility(base, button.facility_type):
                return True
            return True
        return True

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

        minimap_column = layout.minimap_column_rect
        self._draw_rect_outline(minimap_column, (0.15, 0.18, 0.25, 1.0))

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

    def _with_scissor(
        self,
        rect: pygame.Rect,
        window_size: Tuple[int, int],
        draw_callable: Callable[[], None],
    ) -> None:
        width = int(max(0, rect.width))
        height = int(max(0, rect.height))
        if width == 0 or height == 0:
            return

        window_width, window_height = window_size
        x = int(max(0, min(rect.left, window_width)))
        max_width = max(0, window_width - x)
        width = min(width, max_width)

        scissor_y_top = rect.top + rect.height
        y = int(max(0, window_height - scissor_y_top))
        max_height = max(0, window_height - y)
        height = min(height, max_height)

        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glScissor(x, y, width, height)
        try:
            draw_callable()
        finally:
            gl.glDisable(gl.GL_SCISSOR_TEST)

    def _build_facility_icon_meshes(self) -> dict[str, FacilityIconMesh]:
        builders = {
            "ShipwrightFoundry": create_shipwright_foundry_mesh,
            "FleetForge": create_fleet_forge_mesh,
            "ResearchNexus": create_research_nexus_mesh,
            "DefenseGridNode": create_defense_grid_node_mesh,
        }
        meshes: dict[str, FacilityIconMesh] = {}
        for facility_type, builder in builders.items():
            try:
                meshes[facility_type] = self._project_facility_mesh(builder())
            except Exception:
                continue
        return meshes

    def _project_facility_mesh(self, mesh: WireframeMesh) -> FacilityIconMesh:
        projected: List[Vec2] = []
        min_x = math.inf
        max_x = -math.inf
        min_y = math.inf
        max_y = -math.inf
        tilt = 0.32
        for x, y, z in mesh.vertices:
            px = x + y * tilt
            py = -z + y * tilt
            projected.append((px, py))
            min_x = min(min_x, px)
            max_x = max(max_x, px)
            min_y = min(min_y, py)
            max_y = max(max_y, py)
        if not projected:
            projected.append((0.0, 0.0))
            min_x = max_x = min_y = max_y = 0.0
        bounds = (min_x, max_x, min_y, max_y)
        return FacilityIconMesh(projected, list(mesh.segments), bounds)

    def _draw_facility_icon_mesh(
        self,
        rect: pygame.Rect,
        facility_type: str,
        *,
        color: Tuple[float, float, float, float],
    ) -> None:
        icon_mesh = self._facility_icon_meshes.get(facility_type)
        if icon_mesh is None or rect.width <= 0 or rect.height <= 0:
            return
        min_x, max_x, min_y, max_y = icon_mesh.bounds
        span_x = max(1e-3, max_x - min_x)
        span_y = max(1e-3, max_y - min_y)
        padding = 8
        available_w = max(1.0, rect.width - padding * 2)
        available_h = max(1.0, rect.height - padding * 2)
        scale = min(available_w / span_x, available_h / span_y)
        center_x = (min_x + max_x) * 0.5
        center_y = (min_y + max_y) * 0.5
        transformed: List[Vec2] = []
        for px, py in icon_mesh.vertices:
            tx = rect.centerx + (px - center_x) * scale
            ty = rect.centery + (py - center_y) * scale
            transformed.append((tx, ty))

        gl.glColor4f(*color)
        gl.glLineWidth(1.4)
        gl.glBegin(gl.GL_LINES)
        for a, b in icon_mesh.segments:
            ax, ay = transformed[a]
            bx, by = transformed[b]
            gl.glVertex2f(ax, ay)
            gl.glVertex2f(bx, by)
        gl.glEnd()
        gl.glLineWidth(1.0)

    def scroll_context(self, layout: UILayout, wheel_delta: float) -> None:
        rect = layout.context_rect
        if rect.height <= 0:
            return
        scroll_step = 48
        max_scroll = max(0.0, self._context_content_height - rect.height)
        desired = self._context_scroll - wheel_delta * scroll_step
        self._context_scroll = min(max(0.0, desired), max_scroll)

    def _update_context_scroll_bounds(
        self, rect: pygame.Rect, content_height: float
    ) -> None:
        self._context_content_height = max(rect.height, content_height)
        max_scroll = max(0.0, self._context_content_height - rect.height)
        self._context_scroll = min(max(self._context_scroll, 0.0), max_scroll)

    def _context_clip_rect(self, layout: UILayout) -> Optional[pygame.Rect]:
        rect = layout.context_rect
        if rect.width <= 0 or rect.height <= 0:
            return None
        return pygame.Rect(rect.left, rect.top, rect.width, rect.height)

    # ------------------------------------------------------------------
    # Selection summary
    # ------------------------------------------------------------------
    def _draw_selection_summary(self, world: World, rect: pygame.Rect) -> None:
        if world.selected_base is not None:
            self._draw_base_shipyard_panel(world, rect)
            return

        ships = list(world.selected_ships)
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
            f"Acceleration: {focus.acceleration:.0f}",
            f"Turn Rate: {focus.turn_rate:.0f}\u00b0/s",
            f"Visual Range: {focus.visual_range:.0f}",
            f"Radar Range: {focus.radar_range:.0f}",
            f"Firing Range: {focus.firing_range:.0f}",
        ]
        if len(ships) > 1:
            lines.insert(1, f"Group size: {len(ships)} ships")
        self._draw_text_block(rect.left + 16, rect.top + 24, lines)

    def _draw_base_shipyard_panel(self, world: World, rect: pygame.Rect) -> None:
        base = world.selected_base
        if base is None:
            return

        padding = 16
        summary_x = rect.left + padding
        summary_y = rect.top + padding
        lines = [
            f"{base.name} (Base)",
            f"HP: {base.current_health:.0f}/{base.max_health:.0f}",
            f"Armor: {base.armor_value:.0f}",
            f"Shields: {base.current_shields:.0f}/{base.max_shields:.0f}",
            f"Energy: {base.current_energy:.0f}/{base.max_energy:.0f} (+{base.energy_regen_value:.1f}/s)",
            f"Weapon Damage: {base.weapon_damage_value:.0f}",
            f"Flight Speed: {base.flight_speed:.0f}",
            f"Visual Range: {base.visual_range_value:.0f}",
            f"Radar Range: {base.radar_range_value:.0f}",
            f"Firing Range: {base.firing_range_value:.0f}",
        ]
        self._draw_text_block(summary_x, summary_y, lines)

        summary_height = len(lines) * 22
        queue_height = 84
        shipyard_top = summary_y + summary_height + 18
        shipyard_bottom = rect.bottom - queue_height - padding
        if shipyard_bottom < shipyard_top:
            shipyard_top = rect.top + summary_height + 24
            shipyard_bottom = rect.bottom - queue_height - padding
        shipyard_height = max(0, shipyard_bottom - shipyard_top)
        shipyard_rect = pygame.Rect(
            rect.left + padding,
            int(shipyard_top),
            rect.width - 2 * padding,
            int(shipyard_height),
        )

        queue_rect = pygame.Rect(
            rect.left + padding,
            rect.bottom - queue_height,
            rect.width - 2 * padding,
            queue_height - padding // 2,
        )

        ship_defs = sorted(
            world.unlocked_ship_definitions(),
            key=lambda definition: (
                self._ship_class_order(definition.ship_class),
                definition.resource_cost,
            ),
        )
        if shipyard_rect.height > 0:
            self._draw_shipyard_background(shipyard_rect)
            if ship_defs:
                self._draw_shipyard_buttons(world, base, ship_defs, shipyard_rect)
            else:
                self._draw_text_centered(
                    shipyard_rect.centerx,
                    shipyard_rect.centery - 12,
                    "No hulls unlocked yet.",
                    self._muted_text,
                )

        self._draw_ship_queue_display(base, queue_rect)

    def _draw_shipyard_background(self, rect: pygame.Rect) -> None:
        bg = (0.08, 0.1, 0.14, 0.9)
        border = (0.22, 0.28, 0.36, 1.0)
        self._draw_rect(rect, bg)
        self._draw_rect_outline(rect, border)
        self._draw_text_centered(
            rect.centerx,
            rect.top + 10,
            "Ship Construction",
            self._context_text,
        )

    def _draw_shipyard_buttons(
        self,
        world: World,
        base: Base,
        ship_defs: List[ShipDefinition],
        rect: pygame.Rect,
    ) -> None:
        button_area = pygame.Rect(rect.left + 12, rect.top + 32, rect.width - 24, rect.height - 44)
        if button_area.height <= 0 or button_area.width <= 0:
            return
        button_width = 116
        button_height = 112
        spacing = 12
        columns = max(1, int(button_area.width // (button_width + spacing)))
        columns = min(columns, len(ship_defs)) if ship_defs else 1
        if columns == 0:
            columns = 1
        rows = max(1, math.ceil(len(ship_defs) / columns))
        total_width = columns * button_width + (columns - 1) * spacing
        total_height = rows * button_height + (rows - 1) * spacing
        start_x = button_area.left + max(0, (button_area.width - total_width) // 2)
        start_y = button_area.top + max(0, (button_area.height - total_height) // 2)

        for index, definition in enumerate(ship_defs):
            row = index // columns
            col = index % columns
            x = start_x + col * (button_width + spacing)
            y = start_y + row * (button_height + spacing)
            button_rect = pygame.Rect(int(x), int(y), button_width, button_height)
            enabled, status_line = self._ship_button_state(world, base, definition)
            self._draw_shipyard_button(button_rect, definition, enabled, status_line)
            self._production_buttons.append(
                ProductionButton(ship_name=definition.name, rect=button_rect, enabled=enabled)
            )

    def _draw_shipyard_button(
        self,
        rect: pygame.Rect,
        definition: ShipDefinition,
        enabled: bool,
        status_line: Optional[str],
    ) -> None:
        if enabled:
            bg = (0.14, 0.18, 0.26, 0.95)
            text_color = self._text_color
        else:
            bg = (0.08, 0.09, 0.13, 0.8)
            text_color = self._muted_text
        border = (0.3, 0.36, 0.48, 1.0)
        self._draw_rect(rect, bg)
        self._draw_rect_outline(rect, border)

        icon_rect = pygame.Rect(rect.left + 12, rect.top + 10, rect.width - 24, rect.height - 48)
        icon_color = self._ship_class_color(definition.ship_class)
        self._draw_rect(icon_rect, icon_color)
        self._draw_rect_outline(icon_rect, (0.18, 0.22, 0.30, 1.0))
        self._draw_text_centered(
            icon_rect.centerx,
            icon_rect.top + icon_rect.height * 0.35,
            definition.ship_class,
            (20, 24, 32),
        )
        self._draw_text_centered(icon_rect.centerx, icon_rect.bottom - 18, definition.role, self._muted_text)

        self._draw_text_centered(rect.centerx, rect.bottom - 30, definition.name, text_color)
        info_line = f"{definition.build_time:.0f}s | {definition.resource_cost:,}"
        info_color = self._context_text
        if status_line and not enabled:
            info_line = status_line
            info_color = self._muted_text
        self._draw_text_centered(rect.centerx, rect.bottom - 16, info_line, info_color)

    def _draw_ship_queue_display(self, base: Base, rect: pygame.Rect) -> None:
        bg = (0.06, 0.07, 0.1, 0.92)
        border = (0.22, 0.26, 0.34, 1.0)
        self._draw_rect(rect, bg)
        self._draw_rect_outline(rect, border)

        if base is None:
            return

        jobs = self._queue_jobs(base)
        queue_label = f"Queue {len(jobs)}/{base.production.max_jobs}"
        self._draw_text(rect.left + 12, rect.top + 18, queue_label, self._context_text)
        if base.production.queue_full():
            self._draw_text(rect.right - 140, rect.top + 18, "Queue full", self._muted_text)

        if not jobs:
            self._draw_text_centered(rect.centerx, rect.centery, "Queue empty", self._muted_text)
            return

        icon_size = 46
        spacing = 10
        total_width = len(jobs) * icon_size + (len(jobs) - 1) * spacing
        start_x = rect.centerx - total_width * 0.5
        icon_y = rect.top + 32

        for index, job in enumerate(jobs):
            icon_rect = pygame.Rect(
                int(start_x + index * (icon_size + spacing)), int(icon_y), icon_size, icon_size
            )
            color = self._ship_class_color(job.ship_definition.ship_class)
            self._draw_rect(icon_rect, color)
            border_color = self._selected_color if index == 0 else (0.25, 0.3, 0.38, 1.0)
            self._draw_rect_outline(icon_rect, border_color)
            label = job.ship_definition.name[:2].upper()
            self._draw_text_centered(icon_rect.centerx, icon_rect.centery - 10, label, (20, 24, 32))
            self._draw_text_centered(
                icon_rect.centerx,
                icon_rect.centery + 6,
                job.ship_definition.ship_class[:3],
                self._text_color,
            )

    def _queue_jobs(self, base: Base) -> List[ProductionJob]:
        jobs: List[ProductionJob] = []
        active = base.production.active_job
        if active is not None:
            jobs.append(active)
        jobs.extend(base.production.queued_jobs)
        return jobs[: base.production.max_jobs]

    def _ship_class_color(self, ship_class: str) -> Tuple[float, float, float, float]:
        return self._ship_class_colors.get(ship_class, (0.18, 0.22, 0.3, 0.9))

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

    def _draw_text_centered(
        self, center_x: float, y: float, text: str, color: Tuple[int, int, int]
    ) -> None:
        surface = self._font.render(text, True, color)
        data = pygame.image.tostring(surface, "RGBA", True)
        x = center_x - surface.get_width() * 0.5
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
    def _draw_context_panel(
        self, world: World, rect: pygame.Rect, scroll_offset: float
    ) -> float:
        padding = 12
        cursor_x = rect.left + padding
        start_y = rect.top + padding - scroll_offset
        cursor_y = start_y
        selection_kind = self._context_selection_kind(world)
        if selection_kind == "base":
            cursor_y = self._draw_base_context(world, rect, cursor_x, cursor_y)
        elif selection_kind == "worker":
            cursor_y = self._draw_worker_context(world, rect, cursor_x, cursor_y)
        elif selection_kind == "ship":
            cursor_y = self._draw_ship_context(world, cursor_x, cursor_y)
        else:
            cursor_y = self._draw_no_selection_context(cursor_x, cursor_y)
        content_height = cursor_y - start_y + padding
        return max(0.0, content_height)

    def _context_selection_kind(self, world: World) -> str:
        if world.selected_base is not None:
            return "base"
        if world.selected_ships:
            if all(ship.is_worker for ship in world.selected_ships):
                return "worker"
            return "ship"
        return "none"

    def _primary_worker(self, world: World) -> Optional[Ship]:
        for ship in world.selected_ships:
            if ship.is_worker:
                return ship
        return None

    def _draw_base_context(
        self, world: World, rect: pygame.Rect, cursor_x: float, cursor_y: float
    ) -> float:
        base = world.selected_base
        self._draw_text(cursor_x, cursor_y, "Astral Citadel Operations", self._context_text)
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

        cursor_y = self._draw_facility_overview(world, cursor_x, cursor_y, base)
        cursor_y += 18
        cursor_y = self._draw_research_section(world, rect, cursor_x, cursor_y)
        cursor_y += 18
        cursor_y = self._draw_facility_section(world, rect, cursor_x, cursor_y, base)
        cursor_y += 18
        return cursor_y

    def _draw_facility_overview(
        self, world: World, cursor_x: float, cursor_y: float, base: Optional[Base]
    ) -> float:
        self._draw_text(cursor_x, cursor_y, "Operational Facilities", self._context_text)
        cursor_y += 24

        if base is None:
            self._draw_text(cursor_x, cursor_y, "No operational base.", self._muted_text)
            cursor_y += 22
            return cursor_y

        facilities = sorted(
            world.facilities_for_base(base),
            key=lambda facility: facility.name,
        )
        if not facilities:
            self._draw_text(cursor_x, cursor_y, "No facilities online yet.", self._muted_text)
            cursor_y += 22
            return cursor_y

        for facility in facilities:
            cursor_y = self._draw_facility_overview_entry(cursor_x, cursor_y, facility)
        return cursor_y

    def _draw_facility_overview_entry(
        self, cursor_x: float, cursor_y: float, facility: Facility
    ) -> float:
        status = "Online" if facility.online else "Offline"
        status_color = self._text_color if facility.online else self._muted_text
        self._draw_text(cursor_x, cursor_y, facility.name, self._text_color)
        cursor_y += 20
        self._draw_text(cursor_x, cursor_y, status, status_color)
        cursor_y += 18
        summary = facility.definition.description
        self._draw_text(cursor_x + 12, cursor_y, summary, self._muted_text)
        cursor_y += 28
        return cursor_y

    def _draw_worker_context(
        self, world: World, rect: pygame.Rect, cursor_x: float, cursor_y: float
    ) -> float:
        worker = self._primary_worker(world)
        if worker is None:
            self._draw_text(cursor_x, cursor_y, "Select a worker drone.", self._muted_text)
            cursor_y += 22
            return cursor_y
        self._draw_text(cursor_x, cursor_y, f"{worker.name} Construction", self._context_text)
        cursor_y += 24
        income_suffix = ""
        if world.resource_income_rate > 0.0:
            income_suffix = f" (+{world.resource_income_rate:.1f}/s)"
        self._draw_text(
            cursor_x,
            cursor_y,
            f"Resources: {world.resources:.0f}{income_suffix}",
            self._muted_text,
        )
        cursor_y += 22

        pending = getattr(world, "pending_construction", None)
        worker_pending = pending is not None and pending.worker is worker
        cursor_y = self._draw_worker_job_status(world, worker, cursor_x, cursor_y)
        cursor_y += 12

        if worker_pending and pending is not None:
            return self._draw_worker_pending_panel(rect, cursor_x, cursor_y, pending)

        return self._draw_worker_facility_palette(world, rect, cursor_x, cursor_y, worker)

    def _draw_worker_job_status(
        self, world: World, worker: Ship, cursor_x: float, cursor_y: float
    ) -> float:
        jobs = [job for job in world.facility_jobs if job.worker is worker]
        if not jobs:
            self._draw_text(
                cursor_x,
                cursor_y,
                "No active construction orders.",
                self._muted_text,
            )
            cursor_y += 22
            return cursor_y

        for job in jobs:
            if job.state == "travel":
                self._draw_text(
                    cursor_x,
                    cursor_y,
                    f"En route: {job.definition.name}",
                    self._text_color,
                )
                cursor_y += 20
                self._draw_text(
                    cursor_x,
                    cursor_y,
                    "Worker traveling to construction site.",
                    self._muted_text,
                )
                cursor_y += 24
                continue
            total_time = max(0.1, job.definition.build_time)
            progress = 1.0 - max(0.0, job.remaining_time) / total_time
            self._draw_text(
                cursor_x,
                cursor_y,
                f"Constructing: {job.definition.name} ({progress * 100:4.0f}% complete)",
                self._text_color,
            )
            cursor_y += 20
            self._draw_text(
                cursor_x,
                cursor_y,
                f"{max(0.0, job.remaining_time):0.1f}s remaining",
                self._muted_text,
            )
            cursor_y += 24
        return cursor_y

    def _draw_worker_pending_panel(
        self,
        rect: pygame.Rect,
        cursor_x: float,
        cursor_y: float,
        pending: "PendingFacilityPlacement",
    ) -> float:
        definition = pending.definition
        self._draw_text(cursor_x, cursor_y, f"Placing: {definition.name}", self._context_text)
        cursor_y += 24

        preview_height = max(140, min(220, rect.height - int(cursor_y - rect.top) - 120))
        preview_rect = pygame.Rect(
            rect.left + 12,
            int(cursor_y),
            rect.width - 24,
            preview_height,
        )
        self._draw_rect(preview_rect, (0.06, 0.08, 0.12, 0.92))
        self._draw_rect_outline(preview_rect, (0.24, 0.3, 0.42, 1.0))
        icon_rect = preview_rect.inflate(-24, -24)
        icon_rect.height = max(64, icon_rect.height)
        self._draw_facility_icon_mesh(icon_rect, definition.facility_type, color=(0.9, 0.95, 1.0, 1.0))
        cursor_y = preview_rect.bottom + 16

        detail_lines = [
            f"Cost: {definition.resource_cost:,}",
            f"Build Time: {definition.build_time:.0f}s",
            f"Durability: {definition.health} HP / {definition.shields} SH",
        ]
        for line in detail_lines:
            self._draw_text(cursor_x, cursor_y, line, self._text_color)
            cursor_y += 20

        desc_width = rect.width - 24
        for wrapped in self._wrap_text(definition.description, desc_width):
            self._draw_text(cursor_x, cursor_y, wrapped, self._muted_text)
            cursor_y += 20

        cursor_y += 8
        self._draw_text(
            cursor_x,
            cursor_y,
            "Left-click in the world to place the facility.",
            self._context_text,
        )
        cursor_y += 20
        self._draw_text(
            cursor_x,
            cursor_y,
            "Press ESC to cancel and return to the build list.",
            self._muted_text,
        )
        cursor_y += 20
        return cursor_y

    def _draw_worker_facility_palette(
        self,
        world: World,
        rect: pygame.Rect,
        cursor_x: float,
        cursor_y: float,
        worker: Ship,
    ) -> float:
        self._draw_text(cursor_x, cursor_y, "Available Facilities", self._context_text)
        cursor_y += 26
        self._draw_text(
            cursor_x,
            cursor_y,
            "Click a structure to preview and begin placement.",
            self._muted_text,
        )
        cursor_y += 28

        definitions = sorted(all_facility_definitions(), key=lambda definition: definition.name)
        palette_area_top = cursor_y
        palette_bottom = rect.bottom - 8
        palette_rect = pygame.Rect(
            rect.left + 8,
            int(palette_area_top),
            rect.width - 16,
            max(0, int(palette_bottom - palette_area_top)),
        )
        if palette_rect.height <= 0 or palette_rect.width <= 0:
            return cursor_y

        button_width = 156
        button_height = 168
        spacing = 16
        columns = max(1, palette_rect.width // (button_width + spacing))
        columns = min(columns, len(definitions)) or 1
        rows = max(1, math.ceil(len(definitions) / columns)) if definitions else 1

        def total_height() -> int:
            return rows * button_height + (rows - 1) * spacing

        if rows > 0 and total_height() > palette_rect.height:
            # Scale the buttons vertically so every option stays inside the panel.
            available = max(0, palette_rect.height - (rows - 1) * spacing)
            min_height = 96
            if available < rows * min_height:
                # Compress spacing if even the minimum height will not fit.
                spacing = max(8, int(spacing * available / max(1, total_height())))
                available = max(0, palette_rect.height - (rows - 1) * spacing)
            button_height = max(min_height, available // max(1, rows))
            if rows * button_height > max(1, available):
                button_height = max(1, available // rows)

        total_width = columns * button_width + (columns - 1) * spacing
        start_x = palette_rect.left + max(0, (palette_rect.width - total_width) // 2)
        start_y = palette_rect.top + max(0, (palette_rect.height - total_height()) // 2)

        for index, definition in enumerate(definitions):
            row = index // columns
            col = index % columns
            x = start_x + col * (button_width + spacing)
            y = start_y + row * (button_height + spacing)
            button_rect = pygame.Rect(int(x), int(y), button_width, button_height)
            enabled, status_line = world.worker_construction_status(worker, definition)
            self._draw_worker_facility_button(button_rect, definition, enabled, status_line)
            self._facility_buttons.append(
                FacilityButton(
                    facility_type=definition.facility_type,
                    rect=button_rect,
                    enabled=enabled,
                    context="worker",
                )
            )

        return max(cursor_y, start_y + total_height())

    def _draw_worker_facility_button(
        self,
        rect: pygame.Rect,
        definition: FacilityDefinition,
        enabled: bool,
        status_line: Optional[str],
    ) -> None:
        if enabled:
            bg = (0.12, 0.16, 0.24, 0.95)
            border = (0.3, 0.38, 0.52, 1.0)
            title = self._text_color
            detail = self._context_text
            mesh_color = (0.9, 0.96, 1.0, 1.0)
        else:
            bg = (0.07, 0.08, 0.12, 0.8)
            border = (0.2, 0.24, 0.32, 1.0)
            title = self._muted_text
            detail = self._muted_text
            mesh_color = (0.4, 0.45, 0.55, 1.0)
        self._draw_rect(rect, bg)
        self._draw_rect_outline(rect, border)

        icon_size = rect.width - 28
        icon_rect = pygame.Rect(
            rect.left + 14,
            rect.top + 14,
            max(32, icon_size),
            max(32, icon_size),
        )
        icon_rect.height = min(icon_rect.height, rect.height - 64)
        self._draw_facility_icon_mesh(icon_rect, definition.facility_type, color=mesh_color)

        label_y = icon_rect.bottom + 10
        self._draw_text_centered(rect.centerx, label_y, definition.name, title)
        label_y += 18
        info_line = f"{definition.resource_cost:,} | {definition.build_time:.0f}s"
        info_color = detail
        if status_line and not enabled:
            info_line = status_line
            info_color = self._muted_text
        self._draw_text_centered(rect.centerx, label_y, info_line, info_color)

    def _wrap_text(self, text: str, max_width: float) -> List[str]:
        if max_width <= 0:
            return [text]
        words = text.split()
        if not words:
            return [""]
        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}" if current else word
            if self._font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _draw_ship_context(self, world: World, cursor_x: float, cursor_y: float) -> float:
        self._draw_text(cursor_x, cursor_y, "Ship Abilities", self._context_text)
        cursor_y += 24
        ship_count = len(world.selected_ships)
        if ship_count > 1:
            self._draw_text(cursor_x, cursor_y, f"Group size: {ship_count}", self._muted_text)
            cursor_y += 22
        self._draw_text(
            cursor_x,
            cursor_y,
            "No active abilities implemented yet.",
            self._muted_text,
        )
        cursor_y += 22
        self._draw_text(
            cursor_x,
            cursor_y,
            "TODO: Wire ship abilities/stances per ship_guidance.",
            self._muted_text,
        )
        cursor_y += 22
        return cursor_y

    def _draw_no_selection_context(self, cursor_x: float, cursor_y: float) -> float:
        self._draw_text(cursor_x, cursor_y, "Context Actions", self._context_text)
        cursor_y += 24
        self._draw_text(
            cursor_x,
            cursor_y,
            "Select the Astral Citadel to manage research and production.",
            self._muted_text,
        )
        cursor_y += 22
        self._draw_text(
            cursor_x,
            cursor_y,
            "Select ships to access tactical actions.",
            self._muted_text,
        )
        cursor_y += 22
        return cursor_y

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

    def _draw_facility_section(
        self,
        world: World,
        rect: pygame.Rect,
        cursor_x: float,
        cursor_y: float,
        base: Optional[Base],
    ) -> float:
        self._draw_text(cursor_x, cursor_y, "Facilities & Modules", self._context_text)
        cursor_y += 24
        if base is None:
            self._draw_text(cursor_x, cursor_y, "No operational base.", self._muted_text)
            cursor_y += 22
            return cursor_y

        jobs = world.facility_jobs_for_base(base)
        if jobs:
            for job in jobs:
                if job.worker is not None and job.state == "travel":
                    self._draw_text(
                        cursor_x,
                        cursor_y,
                        f"Worker en route: {job.definition.name}",
                        self._text_color,
                    )
                    cursor_y += 20
                    self._draw_text(
                        cursor_x,
                        cursor_y,
                        "Awaiting worker arrival at build site.",
                        self._muted_text,
                    )
                    cursor_y += 24
                    continue
                if job.worker is not None and job.state != "building":
                    continue
                total_time = max(0.1, job.definition.build_time)
                progress = 1.0 - max(0.0, job.remaining_time) / total_time
                self._draw_text(
                    cursor_x,
                    cursor_y,
                    f"Constructing: {job.definition.name} ({progress * 100:4.0f}% complete)",
                    self._text_color,
                )
                cursor_y += 20
                self._draw_text(
                    cursor_x,
                    cursor_y,
                    f"{max(0.0, job.remaining_time):0.1f}s remaining",
                    self._muted_text,
                )
                cursor_y += 24
        else:
            self._draw_text(
                cursor_x,
                cursor_y,
                "No facilities under construction.",
                self._muted_text,
            )
            cursor_y += 22

        definitions = sorted(
            all_facility_definitions(), key=lambda definition: definition.name
        )
        for definition in definitions:
            height = 88
            button_rect = pygame.Rect(rect.left + 8, int(cursor_y), rect.width - 16, height)
            enabled, status_line = world.facility_construction_status(base, definition)
            if world.has_facility(base, definition.facility_type):
                enabled = False
                status_line = "Operational"
            elif world.facility_under_construction(base, definition.facility_type):
                enabled = False
                status_line = "Under construction"
            self._draw_facility_button(button_rect, definition, enabled, status_line)
            self._facility_buttons.append(
                FacilityButton(
                    facility_type=definition.facility_type,
                    rect=button_rect,
                    enabled=enabled,
                    context="base",
                )
            )
            cursor_y += height + 8

        return cursor_y

    # ------------------------------------------------------------------
    # Mini-map
    # ------------------------------------------------------------------
    def _draw_minimap(self, world: World, camera: Camera3D, rect: pygame.Rect) -> None:
        self._draw_rect(rect, self._minimap_bg)

        bounds = self._world_bounds(world)
        visibility: Optional[VisibilityGrid] = getattr(world, "visibility", None)

        for planetoid in world.planetoids:
            if not self._is_position_explored(visibility, planetoid.position):
                continue
            center = self._world_to_minimap(planetoid.position, rect, bounds)
            radius = self._planetoid_radius(planetoid.radius, rect, bounds)
            color = self._planetoid_color(planetoid.controller)
            self._draw_minimap_planetoid(center, radius, color)

        for asteroid in world.asteroids:
            if not self._is_position_explored(visibility, asteroid.position):
                continue
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

        self._draw_fog_overlay(world, rect, bounds)
        self._draw_camera_outline(camera, rect, bounds)
        self._draw_rect_outline(rect, (0.4, 0.45, 0.6, 1.0))
        self._draw_minimap_outline(rect)

    @staticmethod
    def _is_position_explored(
        visibility: Optional[VisibilityGrid], position: Vec2
    ) -> bool:
        if visibility is None:
            return True
        return visibility.is_explored(position)

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
            left = self._world_to_minimap((min_x, min_y), rect, bounds)[0]
            right = self._world_to_minimap((max_x, min_y), rect, bounds)[0]
            if left > right:
                left, right = right, left
            bottom = self._world_to_minimap((min_x, min_y), rect, bounds)[1]
            top = self._world_to_minimap((min_x, max_y), rect, bounds)[1]
            if top > bottom:
                top, bottom = bottom, top
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
        x = rect.left + (1.0 - normalized_x) * rect.width
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

    def _draw_facility_button(
        self,
        rect: pygame.Rect,
        definition: FacilityDefinition,
        enabled: bool,
        status_line: Optional[str],
    ) -> None:
        if enabled:
            bg = (0.13, 0.18, 0.28, 0.95)
            text_color = self._text_color
        else:
            bg = (0.08, 0.09, 0.13, 0.85)
            text_color = self._muted_text
        border = (0.32, 0.4, 0.52, 1.0)
        self._draw_rect(rect, bg)
        self._draw_rect_outline(rect, border)
        text_x = rect.left + 10
        text_y = rect.top + 12
        self._draw_text(text_x, text_y, definition.name, text_color)
        self._draw_text(text_x, text_y + 18, definition.description, self._muted_text)
        self._draw_text(
            text_x,
            text_y + 38,
            f"Cost {definition.resource_cost:,} | {definition.build_time:.0f}s",
            self._context_text,
        )
        self._draw_text(
            text_x,
            text_y + 56,
            f"HP {definition.health:,}  Shields {definition.shields:,}",
            self._context_text,
        )
        if status_line:
            status_color = self._muted_text if not enabled else self._context_text
            self._draw_text(text_x, text_y + 74, status_line, status_color)

    @staticmethod
    def _ship_class_order(ship_class: str) -> int:
        order = {"Utility": -1, "Strike": 0, "Escort": 1, "Line": 2, "Capital": 3}
        return order.get(ship_class, 99)

