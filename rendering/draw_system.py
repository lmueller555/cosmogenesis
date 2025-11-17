"""Wireframe renderer for Cosmogenesis entities."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from OpenGL import GL as gl

import math
import numpy as np
import pygame

from game.camera import Camera3D
from game.entities import Base, Facility, Ship
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
    create_sentinel_cannon_mesh,
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

Vec2 = Tuple[float, float]

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
            "SentinelCannon": create_sentinel_cannon_mesh(),
        }
        self._facility_offsets: Dict[str, Tuple[float, float]] = {
            "ShipwrightFoundry": (-150.0, -70.0),
            "FleetForge": (150.0, -70.0),
            "ResearchNexus": (-150.0, 80.0),
            "DefenseGridNode": (150.0, 80.0),
            "SentinelCannon": (0.0, 160.0),
        }
        self._facility_scales: Dict[str, float] = {
            "ShipwrightFoundry": 0.85,
            "FleetForge": 0.9,
            "ResearchNexus": 0.75,
            "DefenseGridNode": 0.78,
            "SentinelCannon": 0.82,
        }
        self.selection_color: Tuple[float, float, float, float] = (1.0, 0.82, 0.26, 1.0)
        self.enemy_color: Tuple[float, float, float, float] = (1.0, 0.35, 0.35, 1.0)
        self._fog_hidden_color: Tuple[float, float, float, float] = (0.02, 0.04, 0.07, 0.55)
        self._fog_unexplored_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.82)
        self._friendly_beam_color: Tuple[float, float, float] = (0.45, 0.88, 1.0)
        self._enemy_beam_color: Tuple[float, float, float] = (1.0, 0.45, 0.45)
        self._construction_preview_color: Tuple[float, float, float, float] = (
            0.35,
            0.78,
            1.0,
            0.7,
        )
        self._construction_site_color: Tuple[float, float, float, float] = (
            0.95,
            0.35,
            0.35,
            1.0,
        )
        self._overlay_font = pygame.font.SysFont("Consolas", 16)
        self._current_viewport_size: Tuple[int, int] = (0, 0)
        self._move_waypoint_color: Tuple[float, float, float, float] = (0.25, 0.9, 0.45, 0.95)
        self._attack_waypoint_color: Tuple[float, float, float, float] = (0.95, 0.32, 0.32, 0.95)

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

        self._draw_active_construction_sites(world)

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
            self._draw_mesh(
                mesh,
                ship.position,
                scale,
                color=color,
                rotation_degrees=ship.rotation,
            )

        self._draw_pending_construction_preview(world, camera, layout)
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
        rotation_degrees: float = 0.0,
    ) -> None:
        rad = math.radians(rotation_degrees)
        cos_theta = math.cos(rad)
        sin_theta = math.sin(rad)

        transformed: List[Tuple[float, float, float]] = []
        for vx, vy, vz in mesh.vertices:
            world_x = position[0] + (vx * cos_theta - vz * sin_theta) * scale
            world_y = elevation + vy * scale
            world_z = position[1] + (vx * sin_theta + vz * cos_theta) * scale
            transformed.append((world_x, world_y, world_z))

        def _emit(segments: Sequence[Tuple[int, int]], seg_color: Tuple[float, float, float, float]) -> None:
            if not segments:
                return
            gl.glColor4f(*seg_color)
            gl.glBegin(gl.GL_LINES)
            for start_index, end_index in segments:
                gl.glVertex3f(*transformed[start_index])
                gl.glVertex3f(*transformed[end_index])
            gl.glEnd()

        _emit(mesh.segments, color)

        if mesh.colored_segments:
            grouped: Dict[Tuple[float, float, float, float], List[Tuple[int, int]]] = {}
            for segment in mesh.colored_segments:
                grouped.setdefault(segment.color, []).append((segment.start, segment.end))
            for segment_color, pairs in grouped.items():
                _emit(pairs, segment_color)

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
        if world.selected_facility is facility:
            return self.selection_color
        if not facility.online:
            return (0.45, 0.5, 0.62, 1.0)
        return LINE_COLOR

    def _draw_active_construction_sites(self, world: World) -> None:
        jobs = getattr(world, "facility_jobs", None)
        if not jobs:
            return
        for job in jobs:
            if job.worker is None or job.position is None:
                continue
            mesh = self.facility_meshes.get(job.definition.facility_type)
            if mesh is None:
                continue
            scale = self._facility_scale(job.definition.facility_type)
            self._draw_mesh(
                mesh,
                job.position,
                scale,
                color=self._construction_site_color,
                elevation=8.0,
            )

    def _draw_pending_construction_preview(
        self, world: World, camera: Camera3D, layout: UILayout
    ) -> None:
        pending = getattr(world, "pending_construction", None)
        if pending is None:
            return
        mesh = self.facility_meshes.get(pending.definition.facility_type)
        if mesh is None:
            return
        mouse_pos = pygame.mouse.get_pos()
        if not layout.is_in_gameplay(mouse_pos):
            return
        clamped = layout.clamp_to_gameplay(mouse_pos)
        world_pos = camera.screen_to_world(clamped)
        if world_pos is None:
            return
        scale = self._facility_scale(pending.definition.facility_type)
        self._draw_mesh(
            mesh,
            world_pos,
            scale,
            color=self._construction_preview_color,
            elevation=8.0,
        )

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
            self._draw_ship_status_bars(world, camera)
            self._draw_base_progress_bars(world, camera)
            self._draw_research_progress_bars(world, camera)
            self._draw_worker_construction_bars(world, camera)
            self._draw_waypoint_lines(world, camera)
        finally:
            self._end_overlay()

    def _draw_waypoint_lines(self, world: World, camera: Camera3D) -> None:
        width, height = self._current_viewport_size
        if width <= 0 or height <= 0:
            return
        move_commands: list[tuple[Vec2, Vec2, str]] = []
        base = world.selected_base
        if base is not None and base.waypoint is not None:
            move_commands.append((base.position, base.waypoint, "move"))

        for ship in world.selected_ships:
            target = ship.move_target
            if target is None:
                continue
            move_commands.append((ship.position, target, ship.move_behavior))

        if not move_commands:
            return

        for start, end, behavior in move_commands:
            start_screen = camera.world_to_screen(start)
            end_screen = camera.world_to_screen(end)
            if start_screen is None or end_screen is None:
                continue
            color = (
                self._attack_waypoint_color
                if behavior == "attack"
                else self._move_waypoint_color
            )
            self._draw_dashed_line(start_screen, end_screen, color)

    def _draw_dashed_line(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        color: Tuple[float, float, float, float],
        dash_length: float = 12.0,
        gap_length: float = 6.0,
    ) -> None:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = math.hypot(dx, dy)
        if distance <= 0.0:
            return
        direction_x = dx / distance
        direction_y = dy / distance
        gl.glLineWidth(1.0)
        gl.glColor4f(*color)
        t = 0.0
        while t < distance:
            dash_end = min(distance, t + dash_length)
            start_point = (
                start[0] + direction_x * t,
                start[1] + direction_y * t,
            )
            end_point = (
                start[0] + direction_x * dash_end,
                start[1] + direction_y * dash_end,
            )
            gl.glBegin(gl.GL_LINES)
            gl.glVertex2f(*start_point)
            gl.glVertex2f(*end_point)
            gl.glEnd()
            t = dash_end + gap_length

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

    def _draw_research_progress_bars(self, world: World, camera: Camera3D) -> None:
        progress_snapshot = world.research_manager.active_progress()
        if progress_snapshot is None:
            return
        facility_type = progress_snapshot.node.host_facility_type
        matching_facilities = [
            facility
            for facility in world.facilities
            if facility.facility_type == facility_type
            and facility.faction == world.player_faction
        ]
        if not matching_facilities:
            return
        for facility in matching_facilities:
            position = self._facility_render_position(facility)
            screen_pos = camera.world_to_screen(position)
            if screen_pos is None:
                continue
            self._draw_research_progress_bar(
                screen_pos,
                progress_snapshot.node.name,
                progress_snapshot.progress_fraction,
                paused=progress_snapshot.paused,
            )

    def _draw_worker_construction_bars(self, world: World, camera: Camera3D) -> None:
        jobs = getattr(world, "facility_jobs", None)
        if not jobs:
            return
        for job in jobs:
            if job.worker is None or job.position is None or job.state != "building":
                continue
            screen_pos = camera.world_to_screen(job.position)
            if screen_pos is None:
                continue
            total_time = max(0.1, job.definition.build_time)
            progress = 1.0 - max(0.0, job.remaining_time) / total_time
            self._draw_construction_progress_bar(
                screen_pos, job.definition.name, progress
            )

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

    def _draw_research_progress_bar(
        self,
        screen_pos: Tuple[float, float],
        label: str,
        progress: float,
        *,
        paused: bool,
    ) -> None:
        width = 150
        height = 12
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
        progress = max(0.0, min(1.0, progress))
        fill_width = int(inner.width * progress)
        if fill_width > 0:
            fill = pygame.Rect(inner.left, inner.top, fill_width, inner.height)
            fill_color = (0.75, 0.75, 0.45, 0.95) if paused else (0.2, 0.78, 0.55, 0.95)
            self._draw_overlay_rect(fill, fill_color)
        paused_suffix = " (paused)" if paused else ""
        label_text = f"{label}{paused_suffix}"
        label_width, _ = self._overlay_font.size(label_text)
        text_x = rect.centerx - label_width / 2
        text_y = rect.top - 16
        if text_y < 0:
            text_y = rect.bottom + 4
        self._draw_overlay_text(text_x, text_y, label_text, (220, 230, 255))

    def _draw_construction_progress_bar(
        self, screen_pos: Tuple[float, float], label: str, progress: float
    ) -> None:
        width = 140
        height = 10
        bar_offset = 60
        rect = pygame.Rect(
            int(screen_pos[0] - width / 2),
            int(screen_pos[1] - bar_offset - height),
            width,
            height,
        )
        viewport_rect = pygame.Rect(0, 0, *self._current_viewport_size)
        if viewport_rect.width > 0 and viewport_rect.height > 0:
            rect.clamp_ip(viewport_rect.inflate(-8, -8))
        self._draw_overlay_rect(rect, (0.04, 0.05, 0.08, 0.9))
        self._draw_overlay_outline(rect, (0.3, 0.38, 0.52, 1.0))
        inner = rect.inflate(-4, -4)
        fill_width = int(inner.width * max(0.0, min(1.0, progress)))
        if fill_width > 0:
            fill = pygame.Rect(inner.left, inner.top, fill_width, inner.height)
            self._draw_overlay_rect(fill, (0.95, 0.35, 0.35, 0.95))
        label_width, _ = self._overlay_font.size(label)
        text_x = rect.centerx - label_width / 2
        text_y = rect.top - 16
        if text_y < 0:
            text_y = rect.bottom + 4
        self._draw_overlay_text(text_x, text_y, label, (220, 230, 255))

    def _draw_ship_status_bars(self, world: World, camera: Camera3D) -> None:
        grid = getattr(world, "visibility", None)
        viewport_rect = pygame.Rect(0, 0, *self._current_viewport_size)
        for ship in world.ships:
            if ship.faction != world.player_faction:
                if grid is not None and not grid.is_visual(ship.position):
                    continue
            if ship.current_health >= ship.max_health and ship.current_shields >= ship.max_shields:
                continue
            screen_pos = camera.world_to_screen(ship.position)
            if screen_pos is None:
                continue
            self._draw_ship_status_pair(screen_pos, ship, viewport_rect)

    def _draw_ship_status_pair(
        self, screen_pos: Tuple[float, float], ship: Ship, viewport_rect: pygame.Rect
    ) -> None:
        bar_width = 62
        bar_height = 6
        spacing = 2
        vertical_offset = 46
        left = int(screen_pos[0] - bar_width / 2)
        top = int(screen_pos[1] - vertical_offset)
        total_height = bar_height * 2 + spacing
        rect = pygame.Rect(left, top, bar_width, total_height)
        if viewport_rect.width > 0 and viewport_rect.height > 0:
            if viewport_rect.width > 16 and viewport_rect.height > 16:
                rect.clamp_ip(viewport_rect.inflate(-8, -8))
            else:
                rect.clamp_ip(viewport_rect)
            left = rect.left
            top = rect.top
        shield_pct = 0.0 if ship.max_shields <= 0 else ship.current_shields / ship.max_shields
        shield_pct = max(0.0, min(1.0, shield_pct))
        health_pct = 0.0 if ship.max_health <= 0 else ship.current_health / ship.max_health
        health_pct = max(0.0, min(1.0, health_pct))
        shield_rect = pygame.Rect(left, top, bar_width, bar_height)
        health_rect = pygame.Rect(left, top + bar_height + spacing, bar_width, bar_height)
        self._draw_status_bar(shield_rect, shield_pct, (0.45, 0.78, 1.0, 0.95))
        self._draw_status_bar(health_rect, health_pct, self._health_bar_color(health_pct))

    def _draw_status_bar(
        self,
        rect: pygame.Rect,
        percent: float,
        fill_color: Tuple[float, float, float, float],
    ) -> None:
        bg_color = (0.03, 0.04, 0.07, 0.92)
        border_color = (0.2, 0.28, 0.42, 1.0)
        self._draw_overlay_rect(rect, bg_color)
        inner = rect.inflate(-2, -2)
        fill_width = int(max(0, inner.width) * percent)
        if fill_width > 0 and inner.height > 0:
            fill = pygame.Rect(inner.left, inner.top, fill_width, inner.height)
            self._draw_overlay_rect(fill, fill_color)
        self._draw_overlay_outline(rect, border_color)

    @staticmethod
    def _health_bar_color(percent: float) -> Tuple[float, float, float, float]:
        if percent >= 0.8:
            return (0.2, 0.8, 0.32, 0.95)
        if percent >= 0.6:
            return (0.85, 0.75, 0.25, 0.95)
        if percent >= 0.4:
            return (0.95, 0.55, 0.15, 0.95)
        return (0.95, 0.25, 0.2, 0.95)




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
