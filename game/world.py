"""World setup for the Cosmogenesis prototype."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .entities import Base, Planetoid


@dataclass
class World:
    width: float
    height: float
    planetoids: List[Planetoid] = field(default_factory=list)
    bases: List[Base] = field(default_factory=list)

    # TODO: Track fog-of-war state, radar reveals, and additional entity types.


def create_initial_world() -> World:
    """Create a simple sandbox world with one planetoid and one Astral Citadel."""
    world = World(width=4000.0, height=4000.0)

    planetoid = Planetoid(position=(0.0, 0.0), radius=90.0, resource_yield=120)
    world.planetoids.append(planetoid)

    base = Base(position=(160.0, 0.0))
    world.bases.append(base)

    return world
