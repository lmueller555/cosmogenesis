"""World setup for the Cosmogenesis prototype."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

from .entities import Base, Planetoid, Ship
from .ship_registry import ShipDefinition, get_ship_definition

Vec2 = Tuple[float, float]


@dataclass
class World:
    width: float
    height: float
    planetoids: List[Planetoid] = field(default_factory=list)
    bases: List[Base] = field(default_factory=list)
    ships: List[Ship] = field(default_factory=list)
    selected_ships: List[Ship] = field(default_factory=list)

    # TODO: Track fog-of-war state, radar reveals, and additional entity types.

    def update(self, dt: float) -> None:
        """Advance simulation forward by ``dt`` seconds."""

        for ship in self.ships:
            ship.update(dt)

        for base in self.bases:
            completed = base.update(dt)
            for ship_definition in completed:
                self._spawn_ship_from_base(base, ship_definition)

    def issue_move_order(self, destination: Vec2) -> None:
        """Send every selected ship toward ``destination``."""

        for ship in self.selected_ships:
            ship.set_move_target(destination)

    def _spawn_ship_from_base(self, base: Base, ship_definition: ShipDefinition) -> None:
        """Instantiate a finished hull near ``base`` and add it to the fleet."""

        ring_index = base.spawn_serial
        base.spawn_serial += 1
        radius = 220.0 + 45.0 * (ring_index // 12)
        spawn_pos = _spawn_ring_position(base.position, ring_index, radius)
        ship = Ship(position=spawn_pos, definition=ship_definition)
        # TODO: hook into fleet organization / command auras once implemented.
        self.ships.append(ship)


def create_initial_world() -> World:
    """Create a simple sandbox world with one planetoid and one Astral Citadel."""
    world = World(width=4000.0, height=4000.0)

    planetoid = Planetoid(position=(0.0, 0.0), radius=90.0, resource_yield=120)
    world.planetoids.append(planetoid)

    base = Base(position=(160.0, 0.0))
    world.bases.append(base)

    # Seed a handful of strike/escort ships for visualization tests.
    spearling = Ship(position=(400.0, 120.0), definition=get_ship_definition("Spearling"))
    warden = Ship(position=(520.0, -80.0), definition=get_ship_definition("Warden"))
    iron_halberd = Ship(position=(-280.0, 200.0), definition=get_ship_definition("Iron Halberd"))
    world.ships.extend([spearling, warden, iron_halberd])

    # Queue a few autonomous builds so the production loop is observable.
    base.queue_ship("Spearling")
    base.queue_ship("Wisp")
    base.queue_ship("Sunlance")

    return world


def _spawn_ring_position(center: Vec2, index: int, radius: float = 220.0) -> Vec2:
    angle = math.radians((index % 12) * (360.0 / 12))
    return (
        center[0] + math.cos(angle) * radius,
        center[1] + math.sin(angle) * radius,
    )
