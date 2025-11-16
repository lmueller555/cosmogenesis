"""Simple 2D camera utilities for Cosmogenesis."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

Vec2 = Tuple[float, float]


@dataclass
class Camera2D:
    position: Vec2
    viewport_size: Tuple[int, int]
    speed: float = 400.0

    def move(self, direction: Vec2, dt: float) -> None:
        dx, dy = direction
        if dx == 0 and dy == 0:
            return
        px, py = self.position
        self.position = (px + dx * self.speed * dt, py + dy * self.speed * dt)

    def update_viewport(self, size: Tuple[int, int]) -> None:
        self.viewport_size = size

    def world_to_screen(self, world_pos: Vec2) -> Vec2:
        """Convert a world position into screen space."""
        width, height = self.viewport_size
        return (world_pos[0] - self.position[0] + width / 2, world_pos[1] - self.position[1] + height / 2)

    def screen_to_world(self, screen_pos: Vec2) -> Vec2:
        """Convert a screen coordinate back into world space."""
        width, height = self.viewport_size
        return (screen_pos[0] + self.position[0] - width / 2, screen_pos[1] + self.position[1] - height / 2)
