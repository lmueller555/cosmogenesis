"""Entity definitions for Cosmogenesis."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Mapping, Optional, Tuple, Union

from .ship_registry import ShipDefinition
from .production import ProductionQueue, ProductionJob
from .facility_registry import FacilityDefinition

Vec2 = Tuple[float, float]

CombatTarget = Union["Ship", "Facility", "Base"]

PASSIVE_REPAIR_DELAY = 5.0
PASSIVE_REPAIR_RATE = 0.005


def _passive_repair_per_second(max_value: float) -> float:
    if max_value <= 0.0:
        return 0.0
    return float(math.ceil(PASSIVE_REPAIR_RATE * max_value))


@dataclass
class Entity:
    position: Vec2
    rotation: float = field(default=0.0, kw_only=True)
    scale: float = field(default=1.0, kw_only=True)


@dataclass
class Planetoid(Entity):
    radius: float = 80.0
    resource_yield: int = 100
    controller: str = "neutral"

    # TODO: integrate resource extraction logic per `game_guidance`.

    def controlled_by(self, faction: str) -> bool:
        """Return ``True`` if this planetoid currently belongs to ``faction``."""

        return self.controller == faction

    def set_controller(self, faction: str) -> None:
        """Transfer ownership to ``faction`` (no combat logic yet)."""

        self.controller = faction


@dataclass
class Asteroid(Entity):
    """Smaller resource nodes that supplement planetoid income."""

    radius: float = 28.0
    resource_yield: int = 40  # Resources per minute, mirroring planetoid semantics.
    controller: str = "neutral"

    def controlled_by(self, faction: str) -> bool:
        return self.controller == faction

    def set_controller(self, faction: str) -> None:
        self.controller = faction


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
    waypoint: Optional[Vec2] = None
    spawn_serial: int = field(default=0, init=False, repr=False)
    faction: str = "player"
    max_health: float = field(init=False)
    max_shields: float = field(init=False)
    current_health: float = field(init=False)
    current_shields: float = field(init=False)
    armor_value: float = field(init=False)
    max_energy: float = field(init=False)
    current_energy: float = field(init=False)
    energy_regen_value: float = field(init=False)
    visual_range_value: float = field(init=False)
    radar_range_value: float = field(init=False)
    firing_range_value: float = field(init=False)
    weapon_damage_value: float = field(init=False)
    _time_since_damage: float = field(default=PASSIVE_REPAIR_DELAY, init=False, repr=False)

    # TODO: Attach upgrade modules and research integration when systems are implemented.

    def __post_init__(self) -> None:
        self.max_health = float(self.health)
        self.max_shields = float(self.shields)
        self.current_health = self.max_health
        self.current_shields = self.max_shields
        self.armor_value = float(self.armor)
        self.max_energy = float(self.energy)
        self.current_energy = self.max_energy
        self.energy_regen_value = float(self.energy_regen)
        self.visual_range_value = float(self.visual_range)
        self.radar_range_value = float(self.radar_range)
        self.firing_range_value = float(self.firing_range)
        self.weapon_damage_value = float(self.weapon_damage)
        self._time_since_damage = PASSIVE_REPAIR_DELAY

    def queue_ship(self, ship_name: str) -> ProductionJob:
        """Convenience helper so higher-level systems can add ship orders."""

        return self.production.queue_ship(ship_name)

    def update(self, dt: float) -> List[ShipDefinition]:
        """Advance production timers and return finished ship hulls."""

        return self.production.update(dt)

    def apply_stat_multipliers(self, multipliers: Mapping[str, float]) -> None:
        """Apply research-driven stat changes to this base."""

        def mult(attribute: str) -> float:
            return float(multipliers.get(attribute, 1.0))

        prev_max_health = self.max_health
        new_max_health = float(self.health) * mult("health")
        self.max_health = new_max_health
        self.current_health = Ship._scale_current_value(  # reuse helper semantics
            self.current_health, prev_max_health, new_max_health
        )

        prev_max_shields = self.max_shields
        new_max_shields = float(self.shields) * mult("shields")
        self.max_shields = new_max_shields
        self.current_shields = Ship._scale_current_value(
            self.current_shields, prev_max_shields, new_max_shields
        )

        self.armor_value = float(self.armor) * mult("armor")
        self.weapon_damage_value = float(self.weapon_damage) * mult("weapon_damage")
        self.firing_range_value = float(self.firing_range) * mult("firing_range")
        self.visual_range_value = float(self.visual_range) * mult("visual_range")
        self.radar_range_value = float(self.radar_range) * mult("radar_range")
        prev_max_energy = self.max_energy
        new_max_energy = float(self.energy) * mult("energy")
        self.max_energy = new_max_energy
        self.current_energy = Ship._scale_current_value(
            self.current_energy, prev_max_energy, new_max_energy
        )
        self.energy_regen_value = float(self.energy_regen) * mult("energy_regen")

    def repair_full(self) -> None:
        self.current_health = self.max_health
        self.current_shields = self.max_shields
        self._time_since_damage = PASSIVE_REPAIR_DELAY

    def tick_passive_repair(self, dt: float) -> None:
        if dt <= 0.0:
            return
        self._time_since_damage += dt
        if self.current_shields >= self.max_shields:
            return
        if self._time_since_damage < PASSIVE_REPAIR_DELAY:
            return
        repair_rate = _passive_repair_per_second(self.max_shields)
        if repair_rate <= 0.0:
            return
        self.current_shields = min(
            self.max_shields, self.current_shields + repair_rate * dt
        )

    def apply_damage(self, amount: float) -> bool:
        """Apply ``amount`` of damage, returning ``True`` if destroyed."""

        if amount <= 0.0:
            return False
        self._time_since_damage = 0.0
        if self.current_shields > 0.0:
            shield_damage = min(amount, self.current_shields)
            self.current_shields -= shield_damage
            amount -= shield_damage
        if amount > 0.0:
            self.current_health -= amount
        destroyed = self.current_health <= 0.0
        if destroyed:
            self.current_health = 0.0
            self.current_shields = 0.0
        return destroyed


@dataclass
class Facility(Entity):
    """Represents a constructed facility that gates tech trees."""

    definition: FacilityDefinition
    host_base: Optional[Base] = None
    online: bool = True
    current_health: float = field(init=False)
    current_shields: float = field(init=False)
    max_health: float = field(init=False)
    max_shields: float = field(init=False)
    armor_value: float = field(default=0.0, init=False)
    _time_since_damage: float = field(default=PASSIVE_REPAIR_DELAY, init=False, repr=False)
    weapon_damage_value: float = field(init=False)
    firing_range_value: float = field(init=False)
    _weapon_cooldown: float = field(default=0.0, init=False, repr=False)
    _weapon_cycle_time: float = field(default=1.0, init=False, repr=False)

    def __post_init__(self) -> None:
        self.max_health = float(self.definition.health)
        self.max_shields = float(self.definition.shields)
        self.current_health = self.max_health
        self.current_shields = self.max_shields
        # TODO: Populate armor/energy stats once guidance specifies them per facility.
        self._time_since_damage = PASSIVE_REPAIR_DELAY
        self.weapon_damage_value = float(getattr(self.definition, "weapon_damage", 0.0))
        self.firing_range_value = float(getattr(self.definition, "firing_range", 0.0))
        cooldown = float(getattr(self.definition, "weapon_cooldown", 1.0))
        self._weapon_cycle_time = max(0.1, cooldown)
        self._weapon_cooldown = 0.0

    @property
    def facility_type(self) -> str:
        return self.definition.facility_type

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def faction(self) -> str:
        if self.host_base is not None:
            return self.host_base.faction
        return "player"

    def set_online(self, online: bool) -> None:
        """Toggle operational status; ``World`` informs ``ResearchManager``."""

        self.online = online

    def apply_damage(self, amount: float) -> bool:
        """Apply damage to this facility, returning ``True`` if destroyed."""

        if amount <= 0.0:
            return False
        self._time_since_damage = 0.0
        if self.current_shields > 0.0:
            shield_damage = min(amount, self.current_shields)
            self.current_shields -= shield_damage
            amount -= shield_damage
        if amount > 0.0:
            self.current_health -= amount
        destroyed = self.current_health <= 0.0
        if destroyed:
            self.current_health = 0.0
            self.current_shields = 0.0
        return destroyed

    def repair_full(self) -> None:
        self.current_health = self.max_health
        self.current_shields = self.max_shields
        self._time_since_damage = PASSIVE_REPAIR_DELAY

    def tick_passive_repair(self, dt: float) -> None:
        if dt <= 0.0:
            return
        self._time_since_damage += dt
        if self.current_shields >= self.max_shields:
            return
        if self._time_since_damage < PASSIVE_REPAIR_DELAY:
            return
        repair_rate = _passive_repair_per_second(self.max_shields)
        if repair_rate <= 0.0:
            return
        self.current_shields = min(
            self.max_shields, self.current_shields + repair_rate * dt
        )

    def tick_weapon_cooldown(self, dt: float) -> None:
        if dt <= 0.0 or self._weapon_cooldown <= 0.0:
            return
        self._weapon_cooldown = max(0.0, self._weapon_cooldown - dt)

    def ready_to_fire(self) -> bool:
        return (
            self.online
            and self.weapon_damage_value > 0.0
            and self.firing_range_value > 0.0
            and self._weapon_cooldown <= 0.0
        )

    def fire_weapon(self) -> float:
        self._weapon_cooldown = self._weapon_cycle_time
        return self.weapon_damage_value


@dataclass
class WorkerAssignment:
    """Tracks autonomous worker behavior for civilian ships."""

    home_base: Base
    resource_target: Planetoid | Asteroid
    state: str = "travel_to_node"
    mining_duration: float = 0.0
    mining_timer: float = 0.0
    cargo: float = 0.0


@dataclass
class Ship(Entity):
    """Runtime instance of a ship hull from `ship_guidance`."""

    definition: ShipDefinition
    faction: str = "player"
    current_health: float = field(init=False)
    current_shields: float = field(init=False)
    current_energy: float = field(init=False)
    move_target: Optional[Vec2] = None
    move_behavior: str = field(default="move")
    arrival_threshold: float = 6.0
    target: Optional[CombatTarget] = None
    _manual_target: bool = field(default=False, init=False, repr=False)
    _weapon_cooldown: float = 0.0
    max_health: float = field(init=False)
    max_shields: float = field(init=False)
    max_energy: float = field(init=False)
    armor_value: float = field(init=False)
    energy_regen_value: float = field(init=False)
    flight_speed: float = field(init=False)
    acceleration: float = field(init=False)
    turn_rate: float = field(init=False)
    current_speed: float = field(default=0.0, init=False)
    weapon_damage_value: float = field(init=False)
    _visual_range: float = field(init=False)
    _radar_range: float = field(init=False)
    _firing_range: float = field(init=False)
    worker_assignment: Optional[WorkerAssignment] = field(default=None, repr=False)
    collision_radius: float = field(init=False, repr=False)
    _turn_alignment_tolerance: float = field(default=3.0, init=False, repr=False)
    _attack_move_engaged: bool = field(default=False, init=False, repr=False)
    _time_since_damage: float = field(default=PASSIVE_REPAIR_DELAY, init=False, repr=False)

    def __post_init__(self) -> None:
        self.max_health = float(self.definition.health)
        self.max_shields = float(self.definition.shields)
        self.max_energy = float(self.definition.energy)
        self.armor_value = float(self.definition.armor)
        self.energy_regen_value = float(self.definition.energy_regen)
        self.flight_speed = float(self.definition.flight_speed)
        self.acceleration = float(self.definition.acceleration)
        self.turn_rate = float(self.definition.turn_rate)
        self.weapon_damage_value = float(self.definition.weapon_damage)
        self._visual_range = float(self.definition.visual_range)
        self._radar_range = float(self.definition.radar_range)
        self._firing_range = float(self.definition.firing_range)
        self.current_health = self.max_health
        self.current_shields = self.max_shields
        self.current_energy = self.max_energy
        self.rotation = self._wrap_angle(self.rotation)
        self.collision_radius = 0.5 * self._model_scale_for(self.definition.ship_class)
        self._time_since_damage = PASSIVE_REPAIR_DELAY

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def ship_class(self) -> str:
        return self.definition.ship_class

    @property
    def is_worker(self) -> bool:
        return self.definition.is_worker

    @property
    def visual_range(self) -> float:
        return self._visual_range

    @property
    def radar_range(self) -> float:
        return self._radar_range

    @property
    def firing_range(self) -> float:
        return self._firing_range

    def set_move_target(self, target: Optional[Vec2], *, behavior: str = "move") -> None:
        """Assign a new destination for this ship (``None`` clears orders)."""

        self.move_target = target
        if target is None:
            self.move_behavior = "move"
        else:
            self.move_behavior = behavior
        self._attack_move_engaged = False

    def hold_position_for_attack(self, engaged: bool) -> None:
        """Pause/resume movement while executing an attack-move order."""

        if self.move_behavior != "attack":
            self._attack_move_engaged = False
            return
        self._attack_move_engaged = engaged

    def is_enemy(self, other: CombatTarget) -> bool:
        return self.faction != other.faction

    def in_firing_range(self, other: Entity) -> bool:
        dx = other.position[0] - self.position[0]
        dy = other.position[1] - self.position[1]
        return dx * dx + dy * dy <= self.firing_range * self.firing_range

    def has_manual_target(self) -> bool:
        return self._manual_target

    def force_target(self, target: Optional[CombatTarget]) -> None:
        self.target = target
        self._manual_target = target is not None

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
        self._manual_target = False

    def clear_target(self) -> None:
        self.target = None
        self._manual_target = False

    def update(self, dt: float) -> None:
        """Advance ship state – currently only simple point-to-point movement."""

        if dt <= 0.0:
            return

        if self.move_target is None:
            self._decelerate(dt)
            return

        if self.move_behavior == "attack" and self._attack_move_engaged:
            self._decelerate(dt)
            return

        dx = self.move_target[0] - self.position[0]
        dy = self.move_target[1] - self.position[1]
        distance = math.hypot(dx, dy)
        if distance <= self.arrival_threshold:
            self.position = self.move_target
            self.move_target = None
            self.current_speed = 0.0
            return

        desired_angle = math.degrees(math.atan2(dy, dx))
        angle_diff = self._angle_difference(desired_angle, self.rotation)
        max_turn = max(0.0, self.turn_rate) * dt
        if max_turn > 0.0:
            turn_amount = max(-max_turn, min(max_turn, angle_diff))
            self.rotation = self._wrap_angle(self.rotation + turn_amount)
        aligned = abs(self._angle_difference(desired_angle, self.rotation)) <= self._turn_alignment_tolerance

        if not aligned:
            self._decelerate(dt)
            return

        self._accelerate(dt)
        travel_distance = self.current_speed * dt
        if travel_distance <= 0.0:
            return

        if distance <= travel_distance:
            self.position = self.move_target
            self.move_target = None
            self.current_speed = 0.0
            return

        rad = math.radians(self.rotation)
        direction_x = math.cos(rad)
        direction_y = math.sin(rad)
        self.position = (
            self.position[0] + direction_x * travel_distance,
            self.position[1] + direction_y * travel_distance,
        )

    def tick_weapon_cooldown(self, dt: float) -> None:
        if self._weapon_cooldown > 0.0:
            self._weapon_cooldown = max(0.0, self._weapon_cooldown - dt)

    def tick_passive_repair(self, dt: float) -> None:
        if dt <= 0.0:
            return
        self._time_since_damage += dt
        if self.current_shields >= self.max_shields:
            return
        if self._time_since_damage < PASSIVE_REPAIR_DELAY:
            return
        repair_rate = _passive_repair_per_second(self.max_shields)
        if repair_rate <= 0.0:
            return
        self.current_shields = min(
            self.max_shields, self.current_shields + repair_rate * dt
        )

    def can_fire(self) -> bool:
        return self._weapon_cooldown <= 0.0 and self.target is not None

    def deal_damage(self) -> float:
        """Return instantaneous damage output and reset the cooldown timer."""

        # TODO: Pull weapon cadence from guidance once specified.
        self._weapon_cooldown = 1.0
        return self.weapon_damage_value

    def apply_damage(self, amount: float) -> bool:
        """Apply ``amount`` of damage, returning ``True`` if the ship is destroyed."""

        if amount <= 0.0:
            return False
        self._time_since_damage = 0.0

        if self.current_shields > 0.0:
            shield_damage = min(amount, self.current_shields)
            self.current_shields -= shield_damage
            amount -= shield_damage

        if amount > 0.0:
            self.current_health -= amount

        return self.current_health <= 0.0

    def apply_stat_multipliers(self, multipliers: Mapping[str, float]) -> None:
        """Apply cumulative research modifiers provided by ``multipliers``."""

        def mult(attribute: str) -> float:
            return float(multipliers.get(attribute, 1.0))

        prev_max_health = self.max_health
        new_max_health = float(self.definition.health) * mult("health")
        self.max_health = new_max_health
        self.current_health = self._scale_current_value(
            self.current_health, prev_max_health, new_max_health
        )

        prev_max_shields = self.max_shields
        new_max_shields = float(self.definition.shields) * mult("shields")
        self.max_shields = new_max_shields
        self.current_shields = self._scale_current_value(
            self.current_shields, prev_max_shields, new_max_shields
        )

        prev_max_energy = self.max_energy
        new_max_energy = float(self.definition.energy) * mult("energy")
        self.max_energy = new_max_energy
        self.current_energy = self._scale_current_value(
            self.current_energy, prev_max_energy, new_max_energy
        )

        self.armor_value = float(self.definition.armor) * mult("armor")
        self.energy_regen_value = float(self.definition.energy_regen) * mult("energy_regen")
        self.flight_speed = float(self.definition.flight_speed) * mult("flight_speed")
        self.acceleration = float(self.definition.acceleration) * mult("acceleration")
        self.turn_rate = float(self.definition.turn_rate) * mult("turn_rate")
        self.weapon_damage_value = (
            float(self.definition.weapon_damage) * mult("weapon_damage")
        )
        self._visual_range = float(self.definition.visual_range) * mult("visual_range")
        self._radar_range = float(self.definition.radar_range) * mult("radar_range")
        self._firing_range = float(self.definition.firing_range) * mult("firing_range")
        self.current_speed = min(self.current_speed, self.flight_speed)

    def _accelerate(self, dt: float) -> None:
        if self.flight_speed <= 0.0:
            self.current_speed = 0.0
            return
        if self.acceleration <= 0.0:
            self.current_speed = self.flight_speed
            return
        self.current_speed = min(
            self.flight_speed,
            self.current_speed + self.acceleration * dt,
        )

    def _decelerate(self, dt: float) -> None:
        if self.current_speed <= 0.0:
            self.current_speed = 0.0
            return
        if self.acceleration <= 0.0:
            self.current_speed = 0.0
            return
        self.current_speed = max(0.0, self.current_speed - self.acceleration * dt)

    def _angle_difference(self, target_angle: float, current_angle: float) -> float:
        return self._normalize_angle(target_angle - current_angle)

    @staticmethod
    def _wrap_angle(angle: float) -> float:
        wrapped = angle % 360.0
        if wrapped < 0.0:
            wrapped += 360.0
        return wrapped

    @staticmethod
    def _model_scale_for(ship_class: str) -> float:
        """Approximate render scale for each ship class (matches draw system)."""

        if ship_class == "Strike":
            return 0.7
        if ship_class == "Escort":
            return 1.0
        if ship_class == "Line":
            return 1.3
        if ship_class == "Capital":
            return 1.6
        if ship_class == "Utility":
            return 0.6
        return 1.0

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        normalized = (angle + 180.0) % 360.0 - 180.0
        if normalized == -180.0:
            return 180.0
        return normalized

    @staticmethod
    def _scale_current_value(current: float, old_max: float, new_max: float) -> float:
        if new_max <= 0.0:
            return 0.0
        if old_max <= 0.0:
            return new_max
        ratio = current / old_max if old_max > 0 else 1.0
        return min(new_max, ratio * new_max)

    # TODO: Combat stances, AI hooks, aura tracking, etc.
