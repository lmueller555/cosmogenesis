"""Static wireframe meshes used throughout Cosmogenesis."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple


Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]


@dataclass(frozen=True)
class WireframeMesh:
    """Simple container for line segments connecting vertex indices."""

    vertices: Sequence[Vec3]
    segments: Sequence[Tuple[int, int]]

    def transformed(
        self,
        offset: Vec3 = (0.0, 0.0, 0.0),
        scale: float = 1.0,
    ) -> "WireframeMesh":
        """Return a new mesh with vertices offset/scaled for drawing."""

        ox, oy, oz = offset
        transformed_vertices = [
            ((x * scale) + ox, (y * scale) + oy, (z * scale) + oz)
            for x, y, z in self.vertices
        ]
        return WireframeMesh(transformed_vertices, self.segments)


def _extrude_outline(
    vertices_2d: Sequence[Vec2],
    segments_2d: Sequence[Tuple[int, int]],
    height: float,
) -> WireframeMesh:
    """Turn a 2D silhouette into a shallow 3D prism for the angled camera."""

    half = height / 2.0
    base_ring = [(x, -half, y) for x, y in vertices_2d]
    top_ring = [(x, half, y) for x, y in vertices_2d]
    vertices = base_ring + top_ring
    vertex_count = len(vertices_2d)

    segments: List[Tuple[int, int]] = []
    seen = set()

    def add_segment(a: int, b: int) -> None:
        if a == b:
            return
        key = tuple(sorted((a, b)))
        if key in seen:
            return
        seen.add(key)
        segments.append((a, b))

    for a, b in segments_2d:
        add_segment(a, b)
        add_segment(a + vertex_count, b + vertex_count)
        add_segment(a, a + vertex_count)
        add_segment(b, b + vertex_count)

    return WireframeMesh(vertices, segments)


def create_planetoid_mesh(radius: float = 60.0, segments: int = 24) -> WireframeMesh:
    """Approximate a spherical planetoid with multiple great-circle rings."""

    vertices: List[Vec3] = []
    lines: List[Tuple[int, int]] = []

    def add_circle(axis: str, tilt: float = 0.0) -> None:
        start_index = len(vertices)
        for i in range(segments):
            angle = (2 * math.pi * i) / segments
            if axis == "xy":
                x = math.cos(angle) * radius
                y = math.sin(angle) * radius
                z = 0.0
            elif axis == "yz":
                x = 0.0
                y = math.cos(angle) * radius
                z = math.sin(angle) * radius
            else:  # xz plane
                x = math.cos(angle) * radius
                y = 0.0
                z = math.sin(angle) * radius
            if tilt != 0.0:
                # apply a simple rotation around the X axis for variety
                cos_t = math.cos(tilt)
                sin_t = math.sin(tilt)
                y, z = y * cos_t - z * sin_t, y * sin_t + z * cos_t
            vertices.append((x, y, z))
            if i > 0:
                lines.append((start_index + i - 1, start_index + i))
        lines.append((start_index + segments - 1, start_index))

    add_circle("xz")
    add_circle("xy")
    add_circle("yz")
    add_circle("xz", tilt=math.radians(25))
    add_circle("xz", tilt=math.radians(-25))

    return WireframeMesh(vertices, lines)


def create_asteroid_mesh(radius: float = 24.0) -> WireframeMesh:
    """Construct a chunky irregular rock silhouette for asteroid fields."""

    vertices: List[Vec3] = [
        (-0.6 * radius, -0.2 * radius, -0.5 * radius),
        (-0.2 * radius, 0.4 * radius, -0.4 * radius),
        (0.5 * radius, 0.2 * radius, -0.3 * radius),
        (0.3 * radius, -0.5 * radius, -0.6 * radius),
        (-0.4 * radius, -0.3 * radius, 0.4 * radius),
        (-0.1 * radius, 0.5 * radius, 0.5 * radius),
        (0.4 * radius, 0.3 * radius, 0.4 * radius),
        (0.2 * radius, -0.4 * radius, 0.6 * radius),
    ]

    segments: List[Tuple[int, int]] = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
        (0, 5),
        (2, 7),
    ]

    return WireframeMesh(vertices, segments)


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

    return _extrude_outline(vertices, lines, height=80.0)


# --- Ship Meshes ---------------------------------------------------------


def _loop_segments(vertex_count: int) -> List[Tuple[int, int]]:
    return [(i, (i + 1) % vertex_count) for i in range(vertex_count)]


def create_spearling_mesh() -> WireframeMesh:
    """Arrowhead strike craft per `ship_guidance`."""

    vertices: List[Vec2] = [
        (0.0, 18.0),  # nose
        (-10.0, 0.0),
        (-6.0, -8.0),
        (-3.0, -16.0),
        (3.0, -16.0),
        (6.0, -8.0),
        (10.0, 0.0),
        (0.0, -6.0),
    ]
    segments = [
        (0, 1),
        (0, 6),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 6),
        (3, 7),
        (4, 7),
    ]
    return _extrude_outline(vertices, segments, height=8.0)


def create_wisp_mesh() -> WireframeMesh:
    """Needle recon craft with antennae and central diamond."""

    vertices: List[Vec2] = [
        (0.0, 22.0),
        (0.0, -24.0),
        (-3.0, 10.0),
        (3.0, 10.0),
        (-6.0, 12.0),
        (6.0, 12.0),
        (-5.0, -2.0),
        (0.0, -6.0),
        (5.0, -2.0),
    ]
    segments = [
        (0, 1),  # spine
        (2, 3),
        (4, 5),  # antennae
        (2, 6),
        (3, 8),
        (6, 7),
        (7, 8),
        (6, 8),
    ]
    return _extrude_outline(vertices, segments, height=10.0)


def create_daggerwing_mesh() -> WireframeMesh:
    """Broad triangular raider silhouette."""

    vertices: List[Vec2] = [
        (0.0, 24.0),
        (-24.0, -14.0),
        (-6.0, -18.0),
        (0.0, -8.0),
        (6.0, -18.0),
        (24.0, -14.0),
    ]
    segments = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 0),
        (0, 3),
        (0, 2),
        (0, 4),
    ]
    return _extrude_outline(vertices, segments, height=12.0)


def create_skimmer_drone_mesh() -> WireframeMesh:
    """Utility worker craft with a bulbous cargo pod."""

    fuselage_outline: List[Vec2] = [
        (0.0, 22.0),
        (-6.0, 12.0),
        (-4.0, 6.0),
        (-3.0, 0.0),
        (-5.0, -6.0),
        (-8.0, -14.0),
        (-11.0, -24.0),
        (-9.0, -32.0),
        (-5.0, -38.0),
        (0.0, -42.0),
        (5.0, -38.0),
        (9.0, -32.0),
        (11.0, -24.0),
        (8.0, -14.0),
        (5.0, -6.0),
        (3.0, 0.0),
        (4.0, 6.0),
        (6.0, 12.0),
    ]

    cargo_pod = [
        (-6.0, -22.0),
        (-6.0, -34.0),
        (6.0, -22.0),
        (6.0, -34.0),
    ]

    vertices = fuselage_outline + cargo_pod
    segments = _loop_segments(len(fuselage_outline))
    base_index = len(fuselage_outline)
    segments.extend(
        [
            (base_index, base_index + 1),
            (base_index + 1, base_index + 3),
            (base_index + 3, base_index + 2),
            (base_index + 2, base_index),
            (5, base_index),
            (6, base_index + 1),
            (12, base_index + 2),
            (13, base_index + 3),
            (base_index + 1, 9),
            (base_index + 3, 9),
        ]
    )
    return _extrude_outline(vertices, segments, height=9.0)


def create_warden_mesh() -> WireframeMesh:
    vertices: List[Vec2] = [
        (-18.0, 14.0),
        (18.0, 14.0),
        (18.0, -14.0),
        (-18.0, -14.0),
        (-26.0, 6.0),
        (-18.0, 6.0),
        (-18.0, -6.0),
        (-26.0, -6.0),
        (26.0, 6.0),
        (18.0, 6.0),
        (18.0, -6.0),
        (26.0, -6.0),
        (-8.0, 8.0),
        (-4.0, 8.0),
        (-4.0, 4.0),
        (-8.0, 4.0),
        (4.0, -4.0),
        (8.0, -4.0),
        (8.0, -8.0),
        (4.0, -8.0),
    ]
    segments = []
    segments.extend(_loop_segments(4))  # hull
    segments.extend([(4, 5), (5, 6), (6, 7), (7, 4)])
    segments.extend([(8, 9), (9, 10), (10, 11), (11, 8)])
    segments.extend([(12, 13), (13, 14), (14, 15), (15, 12)])
    segments.extend([(16, 17), (17, 18), (18, 19), (19, 16)])
    segments.append((0, 2))
    segments.append((1, 3))
    return _extrude_outline(vertices, segments, height=12.0)


def create_sunlance_mesh() -> WireframeMesh:
    vertices: List[Vec2] = [
        (0.0, 28.0),
        (-14.0, -24.0),
        (14.0, -24.0),
        (-4.0, 12.0),
        (4.0, 12.0),
        (-2.0, -4.0),
        (2.0, -4.0),
        (-6.0, -18.0),
        (6.0, -18.0),
    ]
    segments = [
        (0, 1),
        (0, 2),
        (1, 2),
        (0, 3),
        (0, 4),
        (3, 5),
        (4, 6),
        (5, 7),
        (6, 8),
        (7, 8),
    ]
    return _extrude_outline(vertices, segments, height=10.0)


def create_auric_veil_mesh() -> WireframeMesh:
    vertices: List[Vec2] = [
        (0.0, 16.0),
        (-14.0, 0.0),
        (0.0, -16.0),
        (14.0, 0.0),
        (0.0, 26.0),
        (-18.0, 0.0),
        (0.0, -26.0),
        (18.0, 0.0),
    ]
    segments = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
    ]
    return _extrude_outline(vertices, segments, height=12.0)


def create_iron_halberd_mesh() -> WireframeMesh:
    # The original silhouette was authored with the halberd's nose pointing up the
    # +Y axis. Ships in the simulation treat 0° rotation as facing +X, so the
    # mesh needs to be rotated 90° clockwise to match the flight vector. Without
    # this adjustment, the model would visibly "over rotate" compared to its
    # waypoint heading. Apply the rotation inline so the segment ordering stays
    # identical to the guidance notes.
    outline: List[Vec2] = [
        (-14.0, 30.0),
        (14.0, 30.0),
        (14.0, -30.0),
        (-14.0, -30.0),
        (-30.0, 38.0),
        (30.0, 38.0),
        (-18.0, 36.0),
        (18.0, 36.0),
        (-14.0, -36.0),
        (-8.0, -42.0),
        (8.0, -42.0),
        (14.0, -36.0),
    ]
    vertices: List[Vec2] = [(y, -x) for (x, y) in outline]
    segments = _loop_segments(4)
    segments.extend([(0, 4), (1, 5), (4, 5), (4, 6), (5, 7)])
    segments.extend([(2, 11), (11, 10), (10, 9), (9, 3), (2, 3)])
    return _extrude_outline(vertices, segments, height=16.0)


def create_star_fortress_mesh() -> WireframeMesh:
    vertices: List[Vec2] = [
        (-14.0, 14.0),
        (14.0, 14.0),
        (14.0, -14.0),
        (-14.0, -14.0),
        (0.0, 26.0),
        (0.0, -26.0),
        (-26.0, 0.0),
        (26.0, 0.0),
        (-4.0, 4.0),
        (4.0, 4.0),
        (4.0, -4.0),
        (-4.0, -4.0),
        (-4.0, 30.0),
        (4.0, 30.0),
        (4.0, 22.0),
        (-4.0, 22.0),
        (-4.0, -22.0),
        (4.0, -22.0),
        (4.0, -30.0),
        (-4.0, -30.0),
        (-30.0, 4.0),
        (-22.0, 4.0),
        (-22.0, -4.0),
        (-30.0, -4.0),
        (22.0, 4.0),
        (30.0, 4.0),
        (30.0, -4.0),
        (22.0, -4.0),
    ]
    segments = _loop_segments(4)
    segments.extend([(0, 4), (1, 4), (2, 5), (3, 5), (0, 6), (3, 6), (1, 7), (2, 7)])
    segments.extend(_loop_segments(4))  # will add duplicates but fine for diamond
    segments.extend([(8, 9), (9, 10), (10, 11), (11, 8)])
    segments.extend([(12, 13), (13, 14), (14, 15), (15, 12)])
    segments.extend([(16, 17), (17, 18), (18, 19), (19, 16)])
    segments.extend([(20, 21), (21, 22), (22, 23), (23, 20)])
    segments.extend([(24, 25), (25, 26), (26, 27), (27, 24)])
    return _extrude_outline(vertices, segments, height=18.0)


def create_lance_of_dawn_mesh() -> WireframeMesh:
    vertices: List[Vec2] = [
        (0.0, 48.0),
        (-10.0, 40.0),
        (10.0, 40.0),
        (-6.0, -32.0),
        (6.0, -32.0),
        (-4.0, -50.0),
        (4.0, -50.0),
        (0.0, 36.0),
        (-14.0, -6.0),
        (14.0, -6.0),
    ]
    segments = [
        (0, 1),
        (0, 2),
        (1, 2),
        (1, 3),
        (2, 4),
        (3, 4),
        (3, 5),
        (4, 6),
        (5, 6),
        (0, 7),
        (7, 3),
        (7, 4),
        (1, 8),
        (2, 9),
    ]
    return _extrude_outline(vertices, segments, height=22.0)


def create_titans_ward_mesh() -> WireframeMesh:
    vertices: List[Vec2] = [
        (-40.0, 32.0),
        (40.0, 32.0),
        (40.0, -32.0),
        (-40.0, -32.0),
        (-32.0, 44.0),
        (32.0, 44.0),
        (-20.0, 52.0),
        (20.0, 52.0),
        (-32.0, -44.0),
        (32.0, -44.0),
        (-20.0, -52.0),
        (20.0, -52.0),
        (-12.0, 8.0),
        (-4.0, 8.0),
        (-4.0, 0.0),
        (-12.0, 0.0),
        (4.0, -8.0),
        (12.0, -8.0),
        (12.0, -16.0),
        (4.0, -16.0),
    ]
    segments = _loop_segments(4)
    segments.extend([(0, 4), (4, 5), (5, 1), (4, 6), (5, 7), (6, 7)])
    segments.extend([(2, 8), (8, 9), (9, 3), (8, 10), (9, 11), (10, 11)])
    segments.extend([(12, 13), (13, 14), (14, 15), (15, 12)])
    segments.extend([(16, 17), (17, 18), (18, 19), (19, 16)])
    segments.append((0, 2))
    segments.append((1, 3))
    return _extrude_outline(vertices, segments, height=26.0)


def create_abyssal_crown_mesh() -> WireframeMesh:
    vertices: List[Vec2] = [
        (-26.0, 30.0),
        (26.0, 30.0),
        (26.0, -30.0),
        (-26.0, -30.0),
        (-10.0, 6.0),
        (10.0, 6.0),
        (10.0, -6.0),
        (-10.0, -6.0),
    ]
    # Crown ring pieces
    for angle in range(0, 300, 60):
        rad = math.radians(angle)
        vertices.append((math.cos(rad) * 40.0, math.sin(rad) * 40.0))
    segments = _loop_segments(4)
    segments.append((0, 2))
    segments.append((1, 3))
    segments.extend(_loop_segments(4)[-4:])
    segments.extend([(4, 5), (5, 6), (6, 7), (7, 4)])
    # connect crown arcs and spokes
    crown_start = 8
    crown_vertices = len(vertices) - crown_start
    for i in range(crown_vertices - 1):
        segments.append((crown_start + i, crown_start + i + 1))
    segments.append((crown_start, crown_start + crown_vertices - 1))
    for i in range(crown_vertices):
        segments.append((crown_start + i, crown_start + ((i + 3) % crown_vertices)))
    segments.extend([(4, crown_start), (5, crown_start + 1), (6, crown_start + 2), (7, crown_start + 3)])
    return _extrude_outline(vertices, segments, height=28.0)


def create_oblivion_spire_mesh() -> WireframeMesh:
    vertices: List[Vec2] = [
        (-14.0, 28.0),
        (14.0, 28.0),
        (14.0, -28.0),
        (-14.0, -28.0),
        (-6.0, 60.0),
        (6.0, 60.0),
        (-4.0, 80.0),
        (4.0, 80.0),
        (-10.0, 46.0),
        (10.0, 46.0),
    ]
    segments = _loop_segments(4)
    segments.extend([(0, 4), (1, 5), (4, 5), (4, 6), (5, 7), (6, 7)])
    segments.extend([(4, 8), (5, 9), (8, 9)])
    segments.append((2, 3))
    return _extrude_outline(vertices, segments, height=34.0)


def create_shipwright_foundry_mesh() -> WireframeMesh:
    """Wide cradle-like module reflecting early-ship fabrication berths."""

    outline = [
        (-65.0, -25.0),
        (-50.0, -55.0),
        (50.0, -55.0),
        (65.0, -25.0),
        (65.0, 25.0),
        (50.0, 55.0),
        (-50.0, 55.0),
        (-65.0, 25.0),
    ]
    segments = _loop_segments(len(outline))
    # Internal braces evoke scaffolded gantries.
    braces = [(0, 4), (1, 5), (2, 6), (3, 7), (0, 6), (1, 7)]
    segments.extend(braces)
    return _extrude_outline(outline, segments, height=18.0)


def create_fleet_forge_mesh() -> WireframeMesh:
    """Tall spire with angular shoulders for heavy-hull fabrication."""

    outline = [
        (-35.0, -80.0),
        (0.0, -95.0),
        (35.0, -80.0),
        (65.0, -40.0),
        (65.0, 40.0),
        (35.0, 80.0),
        (0.0, 95.0),
        (-35.0, 80.0),
        (-65.0, 40.0),
        (-65.0, -40.0),
    ]
    segments = _loop_segments(len(outline))
    cross_braces = [(0, 5), (2, 7), (1, 6), (4, 9)]
    segments.extend(cross_braces)
    return _extrude_outline(outline, segments, height=26.0)


def create_research_nexus_mesh() -> WireframeMesh:
    """Hexagonal core with orbiting conduits to emphasize analytics."""

    outline: List[Vec2] = []
    sides = 6
    radius = 55.0
    for i in range(sides):
        angle = (2 * math.pi * i) / sides
        outline.append((math.cos(angle) * radius, math.sin(angle) * radius))
    segments = _loop_segments(len(outline))
    for i in range(sides):
        segments.append((i, (i + 2) % sides))
    return _extrude_outline(outline, segments, height=16.0)


def create_defense_grid_node_mesh() -> WireframeMesh:
    """Square bastion with projecting pylons for the defense grid."""

    outline = [
        (-50.0, -50.0),
        (50.0, -50.0),
        (50.0, 50.0),
        (-50.0, 50.0),
    ]
    pylons = [
        (-80.0, 0.0),
        (0.0, -80.0),
        (80.0, 0.0),
        (0.0, 80.0),
    ]
    segments = _loop_segments(len(outline))
    pylon_start = len(outline)
    outline.extend(pylons)
    for i in range(len(pylons)):
        current = pylon_start + i
        next_index = pylon_start + ((i + 1) % len(pylons))
        segments.append((current, next_index))
    # Connect pylons back to base corners for readability.
    connections = [
        (pylon_start + 0, 0),
        (pylon_start + 1, 1),
        (pylon_start + 2, 2),
        (pylon_start + 3, 3),
    ]
    segments.extend(connections)
    return _extrude_outline(outline, segments, height=20.0)
