"""Static wireframe meshes used throughout Cosmogenesis."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple


Vec2 = Tuple[float, float]


@dataclass(frozen=True)
class WireframeMesh:
    """Simple container for line segments connecting vertex indices."""

    vertices: Sequence[Vec2]
    segments: Sequence[Tuple[int, int]]

    def transformed(self, offset: Vec2 = (0.0, 0.0), scale: float = 1.0) -> "WireframeMesh":
        """Return a new mesh with vertices offset/scaled for drawing."""
        ox, oy = offset
        transformed_vertices = [((x * scale) + ox, (y * scale) + oy) for x, y in self.vertices]
        return WireframeMesh(transformed_vertices, self.segments)


def create_planetoid_mesh(radius: float = 60.0, segments: int = 20) -> WireframeMesh:
    """Approximate a circular planetoid silhouette using line segments."""
    vertices: List[Vec2] = []
    lines: List[Tuple[int, int]] = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        vertices.append((math.cos(angle) * radius, math.sin(angle) * radius))
        if i > 0:
            lines.append((i - 1, i))
    lines.append((segments - 1, 0))
    return WireframeMesh(vertices, lines)


def create_astral_citadel_mesh() -> WireframeMesh:
    """Construct a low-poly representation of the Astral Citadel base."""
    vertices: List[Vec2] = []
    lines: List[Tuple[int, int]] = []

    # Central hexagonal core
    core_radius = 30.0
    for i in range(6):
        angle = (math.pi / 3) * i
        vertices.append((math.cos(angle) * core_radius, math.sin(angle) * core_radius))
        if i > 0:
            lines.append((i - 1, i))
    lines.append((5, 0))

    # Outer ring spokes and arcs (broken crown)
    ring_radius = 70.0
    crown_segments = 8
    crown_start_index = len(vertices)
    for i in range(crown_segments):
        angle = ((math.pi * 1.2) / crown_segments) * i + math.pi / 2.4
        vertices.append((math.cos(angle) * ring_radius, math.sin(angle) * ring_radius))
        if i > 0:
            lines.append((crown_start_index + i - 1, crown_start_index + i))
    # Leave intentional gap by not connecting last to first

    # Spokes connecting crown to core
    for i in range(0, crown_segments, 2):
        core_index = (i // 2) % 6
        lines.append((core_index, crown_start_index + i))

    # Docking arms left/right
    arm_length = 95.0
    arm_offset = 25.0
    left_arm = len(vertices)
    vertices.extend([(-arm_length, arm_offset), (-core_radius, arm_offset), (-core_radius, -arm_offset), (-arm_length, -arm_offset)])
    lines.extend(
        [
            (left_arm, left_arm + 1),
            (left_arm + 1, left_arm + 2),
            (left_arm + 2, left_arm + 3),
            (left_arm + 3, left_arm),
        ]
    )

    right_arm = len(vertices)
    vertices.extend([(arm_length, arm_offset), (core_radius, arm_offset), (core_radius, -arm_offset), (arm_length, -arm_offset)])
    lines.extend(
        [
            (right_arm, right_arm + 1),
            (right_arm + 1, right_arm + 2),
            (right_arm + 2, right_arm + 3),
            (right_arm + 3, right_arm),
        ]
    )

    # Forward siege projector (simple diamond)
    projector_start = len(vertices)
    nose_length = 110.0
    vertices.extend([(0.0, nose_length), (10.0, core_radius), (-10.0, core_radius)])
    lines.extend(
        [
            (projector_start, projector_start + 1),
            (projector_start, projector_start + 2),
            (projector_start + 1, projector_start + 2),
        ]
    )

    return WireframeMesh(vertices, lines)
