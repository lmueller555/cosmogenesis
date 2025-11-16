"""Entity definitions for Cosmogenesis."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from .ship_registry import ShipDefinition

Vec2 = Tuple[float, float]


@dataclass
class Entity:
    position: Vec2
    rotation: float = 0.0
    scale: float = 1.0


@dataclass
class Planetoid(Entity):
    radius: float = 80.0
    resource_yield: int = 100

    # TODO: integrate resource extraction logic per `game_guidance`.


@dataclass
class Base(Entity):
    name: str = "Astral Citadel"
    resource_cost: str = "N/A"
    build_time: str = "N/A"
    health: int = 40000
    armor: int = 400
    shields: int = 20000
    energy: int = 10000
    energy_regen: float = 60.0
    flight_speed: float = 0.0
    visual_range: float = 1400.0
    radar_range: float = 2000.0
    firing_range: float = 1800.0
    weapon_damage: float = 250.0
    # TODO: Attach production queues, upgrade modules, and research integration when systems are implemented.


@dataclass
class Ship(Entity):
    """Runtime instance of a ship hull from `ship_guidance`."""

    definition: ShipDefinition
    current_health: float = field(init=False)
    current_shields: float = field(init=False)
    current_energy: float = field(init=False)

    def __post_init__(self) -> None:
        self.current_health = float(self.definition.health)
        self.current_shields = float(self.definition.shields)
        self.current_energy = float(self.definition.energy)

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def ship_class(self) -> str:
        return self.definition.ship_class

    @property
    def visual_range(self) -> float:
        return self.definition.visual_range

    @property
    def radar_range(self) -> float:
        return self.definition.radar_range

    @property
    def firing_range(self) -> float:
        return self.definition.firing_range

    # TODO: Movement, combat systems, AI hooks, etc.
