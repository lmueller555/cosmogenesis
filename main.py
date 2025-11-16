"""Entry point for the Cosmogenesis prototype."""
from __future__ import annotations

import math
from typing import Tuple

import pygame

from game.camera import Camera2D
from game.selection import (
    SelectionDragState,
    pick_ship,
    select_ships_in_rect,
    select_single_ship,
)
from game.world import create_initial_world
from rendering.draw_system import WireframeRenderer
from rendering.opengl_context import initialize_gl, resize_viewport

WINDOW_SIZE: Tuple[int, int] = (1280, 720)


def handle_camera_input(camera: Camera2D, dt: float) -> None:
    keys = pygame.key.get_pressed()
    direction = [0.0, 0.0]
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        direction[1] += 1.0
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        direction[1] -= 1.0
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        direction[0] += 1.0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        direction[0] -= 1.0

    magnitude = math.hypot(direction[0], direction[1])
    if magnitude > 0.0:
        direction[0] /= magnitude
        direction[1] /= magnitude
        camera.move((direction[0], direction[1]), dt)


def run() -> None:
    pygame.init()
    pygame.display.set_caption("Cosmogenesis Prototype")
    pygame.display.set_mode(WINDOW_SIZE, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)

    initialize_gl(WINDOW_SIZE)

    world = create_initial_world()
    camera = Camera2D(position=(0.0, 0.0), viewport_size=WINDOW_SIZE)
    renderer = WireframeRenderer()
    selection_drag = SelectionDragState()

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                pygame.display.set_mode(event.size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
                resize_viewport(event.size)
                camera.update_viewport(event.size)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    selection_drag.begin(event.pos)
                elif event.button == 3:
                    world_pos = camera.screen_to_world(event.pos)
                    world.issue_move_order(world_pos)
            elif event.type == pygame.MOUSEMOTION:
                if selection_drag.dragging:
                    selection_drag.update(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not selection_drag.dragging:
                    continue
                additive = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                dragged = selection_drag.has_significant_drag()
                start_screen, end_screen = selection_drag.corners()
                selection_drag.finish()
                if dragged:
                    start_world = camera.screen_to_world(start_screen)
                    end_world = camera.screen_to_world(end_screen)
                    select_ships_in_rect(world, start_world, end_world, additive=additive)
                else:
                    world_pos = camera.screen_to_world(event.pos)
                    ship = pick_ship(world, world_pos)
                    select_single_ship(world, ship, additive=additive)

        handle_camera_input(camera, dt)
        world.update(dt)
        selection_box = None
        if selection_drag.dragging and selection_drag.has_significant_drag():
            selection_box = selection_drag.corners()
        renderer.draw_world(world, camera, selection_box=selection_box)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
