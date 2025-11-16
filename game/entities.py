"""Entity definitions for Cosmogenesis."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

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
    move_target: Optional[Vec2] = None
    arrival_threshold: float = 6.0

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

    def set_move_target(self, target: Optional[Vec2]) -> None:
        """Assign a new destination for this ship (``None`` clears orders)."""

        self.move_target = target

    def update(self, dt: float) -> None:
        """Advance ship state – currently only simple point-to-point movement."""

        if self.move_target is None:
            return

        dx = self.move_target[0] - self.position[0]
        dy = self.move_target[1] - self.position[1]
        distance = math.hypot(dx, dy)
        if distance <= self.arrival_threshold or self.definition.flight_speed <= 0.0:
            # Snap to target to avoid jitter and clear the order.
            self.position = self.move_target
            self.move_target = None
            return

        max_step = self.definition.flight_speed * dt
        if max_step <= 0.0:
            return

        if distance <= max_step:
            self.position = self.move_target
            self.move_target = None
            return

        direction_x = dx / distance
        direction_y = dy / distance
        self.position = (
            self.position[0] + direction_x * max_step,
            self.position[1] + direction_y * max_step,
        )

    # TODO: Combat systems, AI hooks, stance tracking, etc.
