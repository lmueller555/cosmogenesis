"""Entity definitions for Cosmogenesis."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

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
