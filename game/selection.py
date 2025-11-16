"""Helpers for selecting ships in the world."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .entities import Ship
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


def pick_ship(world: World, world_pos: Vec2, radius: float = 80.0) -> Optional[Ship]:
    """Return the closest ship within ``radius`` units of ``world_pos``."""
    best_ship: Optional[Ship] = None
    best_distance_sq = radius * radius
    for ship in world.ships:
        dx = ship.position[0] - world_pos[0]
        dy = ship.position[1] - world_pos[1]
        distance_sq = dx * dx + dy * dy
        if distance_sq <= best_distance_sq:
            best_distance_sq = distance_sq
            best_ship = ship
    return best_ship


def _add_to_selection(world: World, ship: Ship) -> None:
    if ship not in world.selected_ships:
        world.selected_ships.append(ship)


def select_single_ship(world: World, ship: Optional[Ship], *, additive: bool = False) -> None:
    """Replace or extend the current selection with ``ship`` if provided."""
    if not additive:
        world.selected_ships.clear()
    if ship is not None:
        _add_to_selection(world, ship)


def select_ships_in_rect(
    world: World,
    corner_a: Vec2,
    corner_b: Vec2,
    *,
    additive: bool = False,
) -> None:
    """Select every ship whose position falls within the axis-aligned rectangle."""

    if not additive:
        world.selected_ships.clear()

    min_x = min(corner_a[0], corner_b[0])
    max_x = max(corner_a[0], corner_b[0])
    min_y = min(corner_a[1], corner_b[1])
    max_y = max(corner_a[1], corner_b[1])

    for ship in world.ships:
        if min_x <= ship.position[0] <= max_x and min_y <= ship.position[1] <= max_y:
            _add_to_selection(world, ship)

    # TODO: Constrain selection to visible/radar-revealed ships once fog of war is online.
