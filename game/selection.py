"""Selection helpers for Cosmogenesis RTS controls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .camera import Camera3D
from .entities import Base, Facility, Ship
from .world import World

Vec2 = Tuple[float, float]


@dataclass
class SelectionDragState:
    """Tracks the drag rectangle while the player is selecting units."""

    dragging: bool = False
    start_screen: Vec2 = (0.0, 0.0)
    current_screen: Vec2 = (0.0, 0.0)

    def begin(self, screen_pos: Vec2) -> None:
        self.dragging = True
        self.start_screen = screen_pos
        self.current_screen = screen_pos

    def update(self, screen_pos: Vec2) -> None:
        if self.dragging:
            self.current_screen = screen_pos

    def finish(self) -> None:
        self.dragging = False

    def has_significant_drag(self, threshold: float = 4.0) -> bool:
        dx = abs(self.current_screen[0] - self.start_screen[0])
        dy = abs(self.current_screen[1] - self.start_screen[1])
        return dx >= threshold or dy >= threshold

    def corners(self) -> Tuple[Vec2, Vec2]:
        return self.start_screen, self.current_screen


def _is_selectable(world: World, ship: Ship) -> bool:
    """Return ``True`` if ``ship`` can currently be interacted with by the player."""

    if ship.faction != world.player_faction:
        return False
    return _is_visible_to_player(world, ship)


def _is_visible_to_player(world: World, ship: Ship) -> bool:
    """Check the world's fog-of-war grid to see if ``ship`` is revealed."""

    grid = getattr(world, "visibility", None)
    if grid is None:
        return True
    # Friendly ships always report their own position through telemetry even if the
    # fog-of-war grid is temporarily missing a mark for the exact cell.
    if ship.faction == world.player_faction:
        return True
    return grid.is_visual(ship.position) or grid.is_radar(ship.position)


def pick_ship(world: World, world_pos: Vec2, radius: float = 80.0) -> Optional[Ship]:
    """Return the closest ship within ``radius`` units of ``world_pos``."""
    best_ship: Optional[Ship] = None
    best_distance_sq = radius * radius
    for ship in world.ships:
        if not _is_selectable(world, ship):
            continue
        dx = ship.position[0] - world_pos[0]
        dy = ship.position[1] - world_pos[1]
        distance_sq = dx * dx + dy * dy
        if distance_sq <= best_distance_sq:
            best_distance_sq = distance_sq
            best_ship = ship
    return best_ship


def pick_enemy_ship(world: World, world_pos: Vec2, radius: float = 80.0) -> Optional[Ship]:
    """Return the closest visible hostile ship near ``world_pos``."""

    best_ship: Optional[Ship] = None
    best_distance_sq = radius * radius
    for ship in world.ships:
        if ship.faction == world.player_faction:
            continue
        if not _is_visible_to_player(world, ship):
            continue
        dx = ship.position[0] - world_pos[0]
        dy = ship.position[1] - world_pos[1]
        distance_sq = dx * dx + dy * dy
        if distance_sq <= best_distance_sq:
            best_distance_sq = distance_sq
            best_ship = ship
    return best_ship


def pick_base(world: World, world_pos: Vec2, radius: float = 220.0) -> Optional[Base]:
    """Return a nearby base if the cursor is close enough to its footprint."""

    best_base: Optional[Base] = None
    best_distance_sq = radius * radius
    for base in world.bases:
        if base.faction != world.player_faction:
            continue
        dx = base.position[0] - world_pos[0]
        dy = base.position[1] - world_pos[1]
        distance_sq = dx * dx + dy * dy
        if distance_sq <= best_distance_sq:
            best_distance_sq = distance_sq
            best_base = base
    return best_base


def _add_to_selection(world: World, ship: Ship) -> None:
    if ship not in world.selected_ships:
        world.selected_ships.append(ship)


def clear_selection(world: World) -> None:
    """Clear every current selection target (ships, bases, facilities)."""

    world.selected_ships.clear()
    world.selected_base = None
    world.selected_facility = None
    cancel = getattr(world, "cancel_pending_construction", None)
    if callable(cancel):
        cancel()


def select_single_ship(world: World, ship: Optional[Ship], *, additive: bool = False) -> None:
    """Replace or extend the current selection with ``ship`` if provided."""
    if not additive:
        clear_selection(world)
    else:
        world.selected_base = None
        world.selected_facility = None
    if ship is not None and _is_selectable(world, ship):
        _add_to_selection(world, ship)


def select_base(world: World, base: Optional[Base]) -> None:
    """Select ``base`` as the active structure, clearing ship selections."""

    clear_selection(world)
    if base is not None:
        world.selected_base = base


def select_facility(world: World, facility: Optional[Facility]) -> None:
    """Focus the given ``facility`` for interaction menus."""

    clear_selection(world)
    if facility is not None and facility in world.facilities:
        base = facility.host_base
        faction = base.faction if base is not None else world.player_faction
        if faction == world.player_faction:
            world.selected_facility = facility


def select_ships_in_rect(
    world: World,
    corner_a: Vec2,
    corner_b: Vec2,
    *,
    additive: bool = False,
) -> None:
    """Select every ship whose position falls within the axis-aligned rectangle."""

    if not additive:
        clear_selection(world)
    else:
        world.selected_base = None
        world.selected_facility = None

    min_x = min(corner_a[0], corner_b[0])
    max_x = max(corner_a[0], corner_b[0])
    min_y = min(corner_a[1], corner_b[1])
    max_y = max(corner_a[1], corner_b[1])

    for ship in world.ships:
        if not _is_selectable(world, ship):
            continue
        if min_x <= ship.position[0] <= max_x and min_y <= ship.position[1] <= max_y:
            _add_to_selection(world, ship)


def select_ships_in_camera_view(
    world: World,
    camera: Camera3D,
    exemplar: Ship,
    *,
    additive: bool = False,
) -> None:
    """Select every friendly ship matching ``exemplar`` that's visible on-screen."""

    if not _is_selectable(world, exemplar):
        return

    viewport_width, viewport_height = camera.viewport_size
    if viewport_width <= 0 or viewport_height <= 0:
        return

    if not additive:
        clear_selection(world)
    else:
        world.selected_base = None
        world.selected_facility = None

    definition_name = exemplar.definition.name
    for ship in world.ships:
        if ship.definition.name != definition_name:
            continue
        if not _is_selectable(world, ship):
            continue
        screen_pos = camera.world_to_screen(ship.position)
        if screen_pos is None:
            continue
        x, y = screen_pos
        if 0.0 <= x <= viewport_width and 0.0 <= y <= viewport_height:
            _add_to_selection(world, ship)


# TODO: Support mixed ship + structure selections once stance/ability commands exist.


def pick_facility(world: World, world_pos: Vec2, radius: float = 120.0) -> Optional[Facility]:
    """Return the closest friendly facility near ``world_pos``."""

    best: Optional[Facility] = None
    best_distance_sq = radius * radius
    for facility in world.facilities:
        base = facility.host_base
        faction = base.faction if base is not None else world.player_faction
        if faction != world.player_faction:
            continue
        dx = facility.position[0] - world_pos[0]
        dy = facility.position[1] - world_pos[1]
        distance_sq = dx * dx + dy * dy
        if distance_sq <= best_distance_sq:
            best_distance_sq = distance_sq
            best = facility
    return best
