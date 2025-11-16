"""Helpers for selecting ships in the world."""
from __future__ import annotations

from typing import Optional, Tuple

from .entities import Ship
from .world import World

Vec2 = Tuple[float, float]


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


def select_single_ship(world: World, ship: Optional[Ship]) -> None:
    """Replace the current selection with ``ship`` if provided."""
    world.selected_ships.clear()
    if ship is not None:
        world.selected_ships.append(ship)
    # TODO: Support multi-select drag boxes and shift-based additive selection per `game_guidance` UX.
