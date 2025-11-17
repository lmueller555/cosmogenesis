"""Entry point for the Cosmogenesis prototype."""
from __future__ import annotations

import math

import pygame

from game.camera import Camera3D
from game.selection import (
    SelectionDragState,
    clear_selection,
    pick_base,
    pick_facility,
    pick_ship,
    select_base,
    select_facility,
    select_ships_in_camera_view,
    select_ships_in_rect,
    select_single_ship,
)
from game.world import create_initial_world, World
from rendering.draw_system import WireframeRenderer
from rendering.opengl_context import initialize_gl, resize_viewport
from ui.layout import UILayout
from ui.panel_renderer import UIPanelRenderer


def handle_camera_input(camera: Camera3D, dt: float) -> None:
    keys = pygame.key.get_pressed()
    direction = [0.0, 0.0]
    if keys[pygame.K_UP]:
        direction[1] += 1.0
    if keys[pygame.K_DOWN]:
        direction[1] -= 1.0
    if keys[pygame.K_RIGHT]:
        direction[0] -= 1.0
    if keys[pygame.K_LEFT]:
        direction[0] += 1.0

    magnitude = math.hypot(direction[0], direction[1])
    if magnitude > 0.0:
        direction[0] /= magnitude
        direction[1] /= magnitude
        camera.move((direction[0], direction[1]), dt)


Vec2 = tuple[float, float]

DOUBLE_CLICK_TIME_MS = 350
DOUBLE_CLICK_MAX_DISTANCE_SQ = 64.0


def _clamp_to_world(world: World, position: Vec2) -> Vec2:
    half_w = world.width * 0.5
    half_h = world.height * 0.5
    x = max(-half_w, min(half_w, position[0]))
    y = max(-half_h, min(half_h, position[1]))
    return (x, y)


def _distance_sq(a: Vec2, b: Vec2) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def _minimap_to_world(world: World, layout: UILayout, point: Vec2) -> Vec2:
    rect = layout.minimap_rect
    if rect.width <= 0 or rect.height <= 0:
        return (0.0, 0.0)
    normalized_x = (rect.right - point[0]) / rect.width
    normalized_y = (rect.bottom - point[1]) / rect.height
    world_x = (normalized_x - 0.5) * world.width
    world_y = (normalized_y - 0.5) * world.height
    return _clamp_to_world(world, (world_x, world_y))


def run() -> None:
    pygame.init()
    pygame.display.set_caption("Cosmogenesis Prototype")
    pygame.display.set_mode(
        (0, 0), pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN
    )
    window_size = pygame.display.get_surface().get_size()
    layout = UILayout(window_size)

    initialize_gl(window_size)

    world = create_initial_world()
    camera = Camera3D(
        position=(0.0, 650.0, -650.0),
        target=(0.0, 0.0, 0.0),
        viewport_size=layout.gameplay_rect.size,
    )
    renderer = WireframeRenderer()
    ui_renderer = UIPanelRenderer()
    selection_drag = SelectionDragState()
    last_left_click_time: int | None = None
    last_left_click_pos: Vec2 = (0.0, 0.0)

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if world.pending_construction is not None:
                    world.cancel_pending_construction()
                    continue
                base = world.selected_base
                if base is not None and base.faction == world.player_faction:
                    if world.cancel_last_ship_order(base):
                        continue
                running = False
            elif event.type == pygame.VIDEORESIZE:
                pygame.display.set_mode(event.size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
                resize_viewport(event.size)
                window_size = event.size
                layout.update(window_size)
                camera.update_viewport(layout.gameplay_rect.size)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if layout.is_in_gameplay(event.pos):
                        clamped = layout.clamp_to_gameplay(event.pos)
                        world_pos = camera.screen_to_world(clamped)
                        if world_pos is not None:
                            clamped_world = _clamp_to_world(world, world_pos)
                            if world.confirm_worker_construction(clamped_world):
                                continue
                        selection_drag.begin(clamped)
                    elif layout.is_in_minimap(event.pos):
                        world_target = _minimap_to_world(world, layout, event.pos)
                        camera.recenter_on(world_target)
                    elif layout.ui_panel_rect.collidepoint(event.pos):
                        ui_renderer.handle_mouse_click(world, layout, event.pos)
                elif event.button == 3:
                    if layout.is_in_gameplay(event.pos):
                        if world.pending_construction is not None:
                            world.cancel_pending_construction()
                            continue
                        clamped = layout.clamp_to_gameplay(event.pos)
                        world_pos = camera.screen_to_world(clamped)
                        if world_pos is None:
                            continue
                        clamped_world = _clamp_to_world(world, world_pos)
                        base = world.selected_base
                        if base is not None and base.faction == world.player_faction:
                            base.waypoint = clamped_world
                            continue
                        behavior = "attack" if pygame.key.get_pressed()[pygame.K_a] else "move"
                        world.issue_move_order(clamped_world, behavior=behavior)
                    elif layout.is_in_minimap(event.pos):
                        world_target = _minimap_to_world(world, layout, event.pos)
                        base = world.selected_base
                        if base is not None and base.faction == world.player_faction:
                            base.waypoint = world_target
                            continue
                        behavior = "attack" if pygame.key.get_pressed()[pygame.K_a] else "move"
                        world.issue_move_order(world_target, behavior=behavior)
            elif event.type == pygame.MOUSEWHEEL:
                mouse_pos = pygame.mouse.get_pos()
                if layout.context_rect.collidepoint(mouse_pos):
                    ui_renderer.scroll_context(layout, event.y)
                else:
                    camera.zoom(event.y)
            elif event.type == pygame.MOUSEMOTION:
                if selection_drag.dragging:
                    selection_drag.update(layout.clamp_to_gameplay(event.pos))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not selection_drag.dragging:
                    continue
                additive = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                dragged = selection_drag.has_significant_drag()
                start_screen, end_screen = selection_drag.corners()
                selection_drag.finish()
                now = pygame.time.get_ticks()
                double_click = (
                    not dragged
                    and last_left_click_time is not None
                    and now - last_left_click_time <= DOUBLE_CLICK_TIME_MS
                    and _distance_sq(event.pos, last_left_click_pos)
                    <= DOUBLE_CLICK_MAX_DISTANCE_SQ
                )
                if dragged:
                    last_left_click_time = None
                else:
                    last_left_click_time = now
                    last_left_click_pos = event.pos
                if dragged:
                    start_world = camera.screen_to_world(start_screen)
                    end_world = camera.screen_to_world(end_screen)
                    select_ships_in_rect(world, start_world, end_world, additive=additive)
                else:
                    attack_pressed = pygame.key.get_pressed()[pygame.K_a]
                    if layout.is_in_gameplay(event.pos):
                        clamped = layout.clamp_to_gameplay(event.pos)
                        world_pos = camera.screen_to_world(clamped)
                        if world_pos is None:
                            continue
                        clamped_world = _clamp_to_world(world, world_pos)
                        if attack_pressed and world.selected_ships:
                            world.issue_move_order(clamped_world, behavior="attack")
                            continue
                        ship = pick_ship(world, world_pos)
                        if ship is not None:
                            if double_click:
                                select_ships_in_camera_view(
                                    world, camera, ship, additive=additive
                                )
                            else:
                                select_single_ship(world, ship, additive=additive)
                            continue
                        facility = pick_facility(world, world_pos)
                        if facility is not None:
                            select_facility(world, facility)
                            continue
                        base = pick_base(world, world_pos)
                        if base is not None:
                            select_base(world, base)
                        elif world.selected_ships:
                            world.issue_move_order(clamped_world, behavior="move")
                        elif not additive:
                            clear_selection(world)

        handle_camera_input(camera, dt)
        world.update(dt)
        selection_box = None
        if selection_drag.dragging and selection_drag.has_significant_drag():
            selection_box = selection_drag.corners()
        renderer.draw_world(world, camera, layout, selection_box=selection_box)
        ui_renderer.draw(world, camera, layout)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
