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
    """Space-station inspired Astral Citadel with a T-shaped profile."""

    scale_factor = 0.75  # Shrink overall footprint by ~25% while keeping silhouette
    vertices: List[Vec2] = []
    segments: List[Tuple[int, int]] = []

    def add_polygon(points: Sequence[Vec2]) -> Tuple[int, int]:
        start = len(vertices)
        vertices.extend(points)
        count = len(points)
        for i in range(count):
            segments.append((start + i, start + ((i + 1) % count)))
        return start, count

    def add_rectangle(
        center_x: float, center_y: float, width: float, height: float
    ) -> Tuple[int, int]:
        half_w = width / 2.0
        half_h = height / 2.0
        return add_polygon(
            [
                (center_x - half_w, center_y - half_h),
                (center_x + half_w, center_y - half_h),
                (center_x + half_w, center_y + half_h),
                (center_x - half_w, center_y + half_h),
            ]
        )

    def add_circle(
        radius: float,
        count: int,
        *,
        center: Vec2 = (0.0, 0.0),
        rotation: float = 0.0,
    ) -> Tuple[int, int]:
        cx, cy = center
        step = (2.0 * math.pi) / count
        points = [
            (
                cx + math.cos(rotation + (step * i)) * radius,
                cy + math.sin(rotation + (step * i)) * radius,
            )
            for i in range(count)
        ]
        return add_polygon(points)

    def connect_scaled(inner: Tuple[int, int], outer: Tuple[int, int]) -> None:
        inner_start, inner_count = inner
        outer_start, outer_count = outer
        factor = max(1, outer_count // inner_count)
        for i in range(outer_count):
            segments.append((outer_start + i, inner_start + (i // factor)))

    def connect_one_to_one(a: Tuple[int, int], b: Tuple[int, int]) -> None:
        start_a, count_a = a
        start_b, count_b = b
        assert count_a == count_b
        for i in range(count_a):
            segments.append((start_a + i, start_b + i))

    def add_spine_lights(center_y_values: Sequence[float]) -> None:
        for y in center_y_values:
            panel = add_rectangle(0.0, y, 18.0, 6.0)
            # Cross braces inside the light strip to emphasize glow panels.
            segments.append((panel[0], panel[0] + 2))
            segments.append((panel[0] + 1, panel[0] + 3))

    def add_arm_light_row(center_x: float, y: float, span: float, count: int) -> None:
        spacing = span / (count - 1)
        for i in range(count):
            x = center_x + (spacing * i)
            light = add_rectangle(x, y, 12.0, 5.0)
            segments.append((light[0], light[0] + 2))
            segments.append((light[0] + 1, light[0] + 3))

    # --- Central spine ---
    spine_outer = add_rectangle(0.0, -20.0, 64.0, 360.0)
    spine_inner = add_rectangle(0.0, -20.0, 36.0, 320.0)
    connect_one_to_one(spine_outer, spine_inner)

    # Reinforcement rings across the tube
    for offset in (-140.0, -40.0, 60.0):
        add_rectangle(0.0, offset, 72.0, 22.0)

    # Command crown and docking collar at the top of the T shape
    crown_outer = add_rectangle(0.0, 140.0, 110.0, 90.0)
    crown_inner = add_rectangle(0.0, 140.0, 70.0, 52.0)
    connect_one_to_one(crown_outer, crown_inner)

    # Lower thruster cap to close the long tube visually
    thruster = add_polygon(
        [(-50.0, -220.0), (50.0, -220.0), (34.0, -260.0), (-34.0, -260.0)]
    )
    connect_scaled(thruster, spine_outer)

    # --- Habitation arms ---
    left_arm = add_rectangle(-135.0, 120.0, 190.0, 44.0)
    right_arm = add_rectangle(135.0, 120.0, 190.0, 44.0)
    connect_scaled(spine_outer, left_arm)
    connect_scaled(spine_outer, right_arm)

    left_adapter = add_rectangle(-220.0, 120.0, 70.0, 70.0)
    right_adapter = add_rectangle(220.0, 120.0, 70.0, 70.0)
    connect_one_to_one(left_arm, left_adapter)
    connect_one_to_one(right_arm, right_adapter)

    # Cylindrical habitation modules
    module_radius_outer = 78.0
    module_radius_inner = 56.0
    left_module_outer = add_circle(
        module_radius_outer, 16, center=(-300.0, 120.0), rotation=math.pi / 16.0
    )
    left_module_inner = add_circle(module_radius_inner, 12, center=(-300.0, 120.0))
    right_module_outer = add_circle(
        module_radius_outer, 16, center=(300.0, 120.0), rotation=math.pi / 16.0
    )
    right_module_inner = add_circle(module_radius_inner, 12, center=(300.0, 120.0))

    connect_scaled(left_module_inner, left_module_outer)
    connect_scaled(right_module_inner, right_module_outer)
    connect_scaled(left_adapter, left_module_outer)
    connect_scaled(right_adapter, right_module_outer)

    # Module endcaps and conduits to imply layered cylinders
    for module_center in (-300.0, 300.0):
        cap = add_rectangle(module_center, 120.0, 40.0, 120.0)
        connect_scaled(cap, left_module_outer if module_center < 0 else right_module_outer)

    # --- Glowing light details ---
    add_spine_lights(y for y in range(-150, 151, 60))
    add_arm_light_row(-210.0, 140.0, 120.0, 3)
    add_arm_light_row(90.0, 140.0, 120.0, 3)

    # Module light bands
    for module_center in (-300.0, 300.0):
        light_ring = add_circle(40.0, 6, center=(module_center, 120.0))
        connect_scaled(
            light_ring,
            left_module_inner if module_center < 0 else right_module_inner,
        )
        # Radial lights to suggest glowing conduits
        start, count = light_ring
        for i in range(count):
            segments.append((start + i, start + ((i + 2) % count)))

    return _extrude_outline(vertices, segments, height=140.0).transformed(scale=scale_factor)


# --- Ship Meshes ---------------------------------------------------------


def _loop_segments(vertex_count: int) -> List[Tuple[int, int]]:
    return [(i, (i + 1) % vertex_count) for i in range(vertex_count)]


def _rotate_xy_clockwise(vertices: Sequence[Vec2]) -> List[Vec2]:
    """Rotate ``vertices`` 90 degrees clockwise around the origin."""

    return [(y, -x) for x, y in vertices]


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

    fuselage_outline: List[Vec2] = _rotate_xy_clockwise(
        [
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
    )

    cargo_pod = _rotate_xy_clockwise(
        [
        (-6.0, -22.0),
        (-6.0, -34.0),
        (6.0, -22.0),
        (6.0, -34.0),
        ]
    )

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
    # The silhouette in the guidance doc was drawn with the halberd's nose
    # pointing down the -Y axis. Ships in the simulation treat 0° rotation as
    # facing +X, so the mesh has to be rotated 90° counter-clockwise to bring
    # the nose in line with the flight vector. Without this adjustment the ship
    # appears to turn around and fly "backwards" when issued a move order. Apply
    # the rotation inline so the segment ordering stays identical to the
    # guidance notes.
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
    vertices: List[Vec2] = [(-y, x) for (x, y) in outline]
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


def create_sentinel_cannon_mesh() -> WireframeMesh:
    """Compact turret base with a forward cannon barrel."""

    base_outline = [
        (0.0, -55.0),
        (35.0, -35.0),
        (55.0, 0.0),
        (35.0, 35.0),
        (0.0, 55.0),
        (-35.0, 35.0),
        (-55.0, 0.0),
        (-35.0, -35.0),
    ]
    segments = _loop_segments(len(base_outline))
    # Cross braces for the octagonal base
    braces = [(0, 4), (1, 5), (2, 6), (3, 7)]
    segments.extend(braces)

    # Cannon barrel protrusion
    barrel_start = len(base_outline)
    barrel = [
        (-8.0, -55.0),
        (-4.0, -105.0),
        (4.0, -105.0),
        (8.0, -55.0),
    ]
    base_outline.extend(barrel)
    segments.extend(
        [
            (barrel_start + i, barrel_start + ((i + 1) % len(barrel)))
            for i in range(len(barrel))
        ]
    )
    # Connect barrel back to base corners to imply mounting hardware.
    segments.extend([(0, barrel_start), (0, barrel_start + 3), (7, barrel_start), (7, barrel_start + 3)])

    return _extrude_outline(base_outline, segments, height=22.0)
