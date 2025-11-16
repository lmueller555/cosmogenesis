"""Simple AI controller for enemy forces.

This module keeps the sandbox aligned with ``game_guidance`` expectations by
ensuring hostile ships pressure the player and periodically receive
reinforcements. The intent is to provide a minimal-yet-extensible foundation
for future economic or tactical behaviors.
"""
from __future__ import annotations

import math
from itertools import cycle
from typing import List, TYPE_CHECKING

from .entities import Ship
from .ship_registry import get_ship_definition

if TYPE_CHECKING:  # pragma: no cover - circular import safe guard
    from .world import World, Vec2


class EnemyAIController:
    """Directs hostile ships and schedules reinforcement waves."""

    def __init__(self, world: "World") -> None:
        self._world = world
        self._spawn_interval = 30.0
        self._spawn_timer = 8.0
        self._max_active = 10
        self._ship_cycle = cycle(
            (
                "Spearling",
                "Wisp",
                "Daggerwing",
                "Sunlance",
                "Iron Halberd",
            )
        )
        self._spawn_serial = 0
        half_w = self._world.width * 0.5
        half_h = self._world.height * 0.5
        # Stage enemy reinforcements just outside the visible arena to mimic
        # incursions from deep space.
        self._staging_center = (-half_w * 0.8, half_h * 0.65)
        self._staging_ring_step = 140.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if dt <= 0.0:
            return
        self._command_existing_fleet()
        self._spawn_timer -= dt
        if self._spawn_timer <= 0.0:
            self._spawn_timer += self._spawn_interval
            self._try_spawn_reinforcement()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _command_existing_fleet(self) -> None:
        base = self._world.player_primary_base()
        if base is None:
            return
        target_position = base.position
        for ship in self._enemy_ships():
            if ship.move_target is None:
                ship.set_move_target(target_position)

    def _try_spawn_reinforcement(self) -> None:
        if len(self._enemy_ships()) >= self._max_active:
            return
        ship_name = next(self._ship_cycle)
        try:
            definition = get_ship_definition(ship_name)
        except KeyError:
            return
        spawn_pos = self._spawn_point(self._spawn_serial)
        self._spawn_serial += 1
        ship = Ship(position=spawn_pos, definition=definition, faction="enemy")
        base = self._world.player_primary_base()
        if base is not None:
            ship.set_move_target(base.position)
        self._world.ships.append(ship)

    def _enemy_ships(self) -> List[Ship]:
        return [ship for ship in self._world.ships if ship.faction == "enemy"]

    def _spawn_point(self, serial: int) -> "Vec2":
        ring_index = serial // 8
        slot = serial % 8
        radius = 200.0 + self._staging_ring_step * ring_index
        angle = (slot / 8.0) * (2.0 * math.pi)
        offset_x = math.cos(angle) * radius
        offset_y = math.sin(angle) * radius
        center_x, center_y = self._staging_center
        return (center_x + offset_x, center_y + offset_y)
