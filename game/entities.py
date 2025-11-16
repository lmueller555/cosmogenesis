"""Entity definitions for Cosmogenesis."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .ship_registry import ShipDefinition
from .production import ProductionQueue, ProductionJob

Vec2 = Tuple[float, float]


@dataclass
class Entity:
    position: Vec2
    rotation: float = field(default=0.0, kw_only=True)
    scale: float = field(default=1.0, kw_only=True)


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
    production: ProductionQueue = field(default_factory=ProductionQueue)
    spawn_serial: int = field(default=0, init=False, repr=False)
    faction: str = "player"

    # TODO: Attach upgrade modules and research integration when systems are implemented.

    def queue_ship(self, ship_name: str) -> ProductionJob:
        """Convenience helper so higher-level systems can add ship orders."""

        return self.production.queue_ship(ship_name)

    def update(self, dt: float) -> List[ShipDefinition]:
        """Advance production timers and return finished ship hulls."""

        return self.production.update(dt)


@dataclass
class Ship(Entity):
    """Runtime instance of a ship hull from `ship_guidance`."""

    definition: ShipDefinition
    faction: str = "player"
    current_health: float = field(init=False)
    current_shields: float = field(init=False)
    current_energy: float = field(init=False)
    move_target: Optional[Vec2] = None
    arrival_threshold: float = 6.0
    target: Optional["Ship"] = None
    _weapon_cooldown: float = 0.0

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

    def is_enemy(self, other: "Ship") -> bool:
        return self.faction != other.faction

    def in_firing_range(self, other: "Ship") -> bool:
        dx = other.position[0] - self.position[0]
        dy = other.position[1] - self.position[1]
        return dx * dx + dy * dy <= self.firing_range * self.firing_range

    def acquire_target(self, candidates: List["Ship"]) -> None:
        """Pick the closest valid enemy from ``candidates``."""

        best_target: Optional[Ship] = None
        best_distance_sq = float("inf")
        for ship in candidates:
            if not self.is_enemy(ship):
                continue
            dx = ship.position[0] - self.position[0]
            dy = ship.position[1] - self.position[1]
            distance_sq = dx * dx + dy * dy
            if distance_sq <= self.firing_range * self.firing_range and distance_sq < best_distance_sq:
                best_distance_sq = distance_sq
                best_target = ship
        self.target = best_target

    def clear_target(self) -> None:
        self.target = None

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

    def tick_weapon_cooldown(self, dt: float) -> None:
        if self._weapon_cooldown > 0.0:
            self._weapon_cooldown = max(0.0, self._weapon_cooldown - dt)

    def can_fire(self) -> bool:
        return self._weapon_cooldown <= 0.0 and self.target is not None

    def deal_damage(self) -> float:
        """Return instantaneous damage output and reset the cooldown timer."""

        # TODO: Pull weapon cadence from guidance once specified.
        self._weapon_cooldown = 1.0
        return self.definition.weapon_damage

    def apply_damage(self, amount: float) -> bool:
        """Apply ``amount`` of damage, returning ``True`` if the ship is destroyed."""

        if amount <= 0.0:
            return False

        if self.current_shields > 0.0:
            shield_damage = min(amount, self.current_shields)
            self.current_shields -= shield_damage
            amount -= shield_damage

        if amount > 0.0:
            self.current_health -= amount

        return self.current_health <= 0.0

    # TODO: Combat stances, AI hooks, aura tracking, etc.
