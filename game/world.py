"""World setup for the Cosmogenesis prototype."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .entities import Base, Planetoid, Ship
from .ship_registry import get_ship_definition


@dataclass
class World:
    width: float
    height: float
    planetoids: List[Planetoid] = field(default_factory=list)
    bases: List[Base] = field(default_factory=list)
    ships: List[Ship] = field(default_factory=list)

    # TODO: Track fog-of-war state, radar reveals, and additional entity types.


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

    return world
