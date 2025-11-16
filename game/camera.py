"""3D camera utilities for Cosmogenesis."""
from __future__ import annotations

"""3D camera utilities for Cosmogenesis."""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


def _look_at_matrix(position: Vec3, target: Vec3, up: Vec3) -> np.ndarray:
    pos = np.array(position, dtype=np.float32)
    tgt = np.array(target, dtype=np.float32)
    up_vec = np.array(up, dtype=np.float32)

    forward = _normalize(tgt - pos)
    side = _normalize(np.cross(forward, up_vec))
    true_up = np.cross(side, forward)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] = side
    view[1, :3] = true_up
    view[2, :3] = -forward
    view[0, 3] = -np.dot(side, pos)
    view[1, 3] = -np.dot(true_up, pos)
    view[2, 3] = np.dot(forward, pos)
    return view


def _perspective_matrix(fov_degrees: float, aspect: float, near: float, far: float) -> np.ndarray:
    perspective = np.zeros((4, 4), dtype=np.float32)
    f = 1.0 / math.tan(math.radians(fov_degrees) / 2.0)
    perspective[0, 0] = f / aspect
    perspective[1, 1] = f
    perspective[2, 2] = (far + near) / (near - far)
    perspective[2, 3] = (2 * far * near) / (near - far)
    perspective[3, 2] = -1.0
    return perspective


@dataclass
class Camera3D:
    position: Vec3
    target: Vec3
    viewport_size: Tuple[int, int]
    speed: float = 420.0
    min_zoom: float = 320.0
    max_zoom: float = 2200.0
    zoom_speed: float = 90.0
    fov: float = 60.0
    near_clip: float = 1.0
    far_clip: float = 5000.0
    up: Vec3 = (0.0, 1.0, 0.0)

    def move(self, direction: Vec2, dt: float) -> None:
        dx, dz = direction
        if dx == 0 and dz == 0:
            return
        movement = (dx * self.speed * dt, 0.0, dz * self.speed * dt)
        self.position = (
            self.position[0] + movement[0],
            self.position[1] + movement[1],
            self.position[2] + movement[2],
        )
        self.target = (
            self.target[0] + movement[0],
            self.target[1] + movement[1],
            self.target[2] + movement[2],
        )

    def zoom(self, scroll_delta: float) -> None:
        """Move the camera closer/farther from the target while preserving angle."""

        view_dir = self._view_direction()
        if np.linalg.norm(view_dir) == 0:
            return
        current_distance = np.linalg.norm(np.array(self.position) - np.array(self.target))
        desired = current_distance - scroll_delta * self.zoom_speed
        clamped = max(self.min_zoom, min(self.max_zoom, desired))
        self.position = (
            self.target[0] - view_dir[0] * clamped,
            self.target[1] - view_dir[1] * clamped,
            self.target[2] - view_dir[2] * clamped,
        )

    def update_viewport(self, size: Tuple[int, int]) -> None:
        self.viewport_size = size

    def view_matrix(self) -> np.ndarray:
        return _look_at_matrix(self.position, self.target, self.up)

    def projection_matrix(self) -> np.ndarray:
        width, height = self.viewport_size
        aspect = width / height if height > 0 else 1.0
        return _perspective_matrix(self.fov, aspect, self.near_clip, self.far_clip)

    def view_projection_matrix(self) -> np.ndarray:
        return self.projection_matrix() @ self.view_matrix()

    def _view_direction(self) -> np.ndarray:
        pos = np.array(self.position, dtype=np.float32)
        tgt = np.array(self.target, dtype=np.float32)
        return _normalize(pos - tgt)

    def world_to_screen(self, world_pos: Vec2, elevation: float = 0.0) -> Optional[Vec2]:
        """Project a point on the world plane (y=elevation) to screen coordinates."""

        x, z = world_pos
        point = np.array([x, elevation, z, 1.0], dtype=np.float32)
        clip = self.view_projection_matrix() @ point
        w = clip[3]
        if w == 0:
            return None
        ndc = clip[:3] / w
        if ndc[2] < -1 or ndc[2] > 1:
            return None
        width, height = self.viewport_size
        screen_x = float((ndc[0] + 1.0) * 0.5 * width)
        screen_y = float((1.0 - ndc[1]) * 0.5 * height)
        return (screen_x, screen_y)

    def screen_to_world(self, screen_pos: Vec2, plane_height: float = 0.0) -> Vec2:
        """Intersect a ray from the camera through ``screen_pos`` with the world plane."""

        width, height = self.viewport_size
        if width == 0 or height == 0:
            return (0.0, 0.0)
        x = (2.0 * screen_pos[0] / width) - 1.0
        y = 1.0 - (2.0 * screen_pos[1] / height)
        inv_vp = np.linalg.inv(self.view_projection_matrix())
        near_point = np.array([x, y, -1.0, 1.0], dtype=np.float32)
        far_point = np.array([x, y, 1.0, 1.0], dtype=np.float32)

        near_world = inv_vp @ near_point
        far_world = inv_vp @ far_point
        if near_world[3] != 0:
            near_world /= near_world[3]
        if far_world[3] != 0:
            far_world /= far_world[3]

        direction = far_world - near_world
        if abs(direction[1]) < 1e-5:
            return (float(near_world[0]), float(near_world[2]))
        t = (plane_height - near_world[1]) / direction[1]
        intersection = near_world + direction * t
        return (float(intersection[0]), float(intersection[2]))
