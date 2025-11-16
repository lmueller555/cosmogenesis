"""World setup for the Cosmogenesis prototype."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .entities import Base, Planetoid, Ship
from .ship_registry import (
    ShipDefinition,
    all_ship_definitions,
    get_ship_definition,
)
from .research import ResearchManager, ResearchNode

Vec2 = Tuple[float, float]


@dataclass
class World:
    width: float
    height: float
    planetoids: List[Planetoid] = field(default_factory=list)
    bases: List[Base] = field(default_factory=list)
    ships: List[Ship] = field(default_factory=list)
    selected_ships: List[Ship] = field(default_factory=list)
    resources: float = 20_000.0
    research_manager: ResearchManager = field(default_factory=ResearchManager)

    # TODO: Track fog-of-war state, radar reveals, and additional entity types.

    def update(self, dt: float) -> None:
        """Advance simulation forward by ``dt`` seconds."""

        for ship in self.ships:
            ship.update(dt)
            ship.tick_weapon_cooldown(dt)

        for base in self.bases:
            completed = base.update(dt)
            for ship_definition in completed:
                self._spawn_ship_from_base(base, ship_definition)

        self._update_combat(dt)
        completed_research = self.research_manager.update(dt)
        if completed_research is not None:
            # TODO: propagate stat bonuses / notifications once UI exists.
            self._refresh_research_bonuses()

    def issue_move_order(self, destination: Vec2) -> None:
        """Send every selected ship toward ``destination``."""

        for ship in self.selected_ships:
            ship.set_move_target(destination)

    def queue_ship(self, base: Base, ship_name: str) -> bool:
        """Queue ``ship_name`` at ``base`` if research + resources allow it."""

        if base not in self.bases:
            return False

        try:
            definition = get_ship_definition(ship_name)
        except KeyError:
            return False

        if not self.research_manager.is_ship_unlocked(ship_name):
            return False

        if self.resources < definition.resource_cost:
            return False

        base.queue_ship(ship_name)
        self.resources -= definition.resource_cost
        return True

    def player_primary_base(self) -> Optional[Base]:
        """Return the first operational player-controlled base, if any."""

        for base in self.bases:
            if base.faction == "player":
                return base
        return None

    def unlocked_ship_definitions(self) -> List[ShipDefinition]:
        """Expose the ship hulls currently unlocked for production."""

        unlocked: List[ShipDefinition] = []
        for definition in all_ship_definitions():
            if self.research_manager.is_ship_unlocked(definition.name):
                unlocked.append(definition)
        return unlocked

    def try_start_research(self, node_id: str) -> bool:
        """Attempt to start researching ``node_id`` using shared resources."""

        node = self._node(node_id)
        if node is None:
            return False
        if not self.research_manager.start(node_id, available_resources=self.resources):
            return False
        self.resources -= node.resource_cost
        return True

    def available_research(self) -> List[ResearchNode]:
        """Expose nodes currently available for UI / debugging."""

        return self.research_manager.available_nodes(available_resources=self.resources)

    def _node(self, node_id: str) -> Optional[ResearchNode]:
        for node in self.research_manager.nodes():
            if node.id == node_id:
                return node
        return None

    def _spawn_ship_from_base(self, base: Base, ship_definition: ShipDefinition) -> None:
        """Instantiate a finished hull near ``base`` and add it to the fleet."""

        ring_index = base.spawn_serial
        base.spawn_serial += 1
        radius = 220.0 + 45.0 * (ring_index // 12)
        spawn_pos = _spawn_ring_position(base.position, ring_index, radius)
        ship = Ship(position=spawn_pos, definition=ship_definition, faction=base.faction)
        # TODO: hook into fleet organization / command auras once implemented.
        self._apply_ship_research(ship)
        self.ships.append(ship)

    def _update_combat(self, dt: float) -> None:
        """Resolve simplistic auto-attacks between hostile ships."""

        destroyed: List[Ship] = []
        for ship in self.ships:
            if ship.target is None or ship.target not in self.ships or not ship.in_firing_range(ship.target):
                ship.acquire_target(self.ships)
            if ship.target is None:
                continue
            if not ship.is_enemy(ship.target):
                ship.clear_target()
                continue
            if ship.can_fire():
                damage = ship.deal_damage()
                # TODO: Replace with burst fire logic once cadence guidance is available.
                if ship.target.apply_damage(damage):
                    destroyed.append(ship.target)
                    ship.clear_target()

        if destroyed:
            for ship in destroyed:
                if ship in self.ships:
                    self.ships.remove(ship)
                if ship in self.selected_ships:
                    self.selected_ships.remove(ship)

    def _apply_ship_research(self, ship: Ship) -> None:
        if ship.faction != "player":
            return
        multipliers = self.research_manager.ship_stat_multipliers(ship.definition.ship_class)
        ship.apply_stat_multipliers(multipliers)

    def _apply_base_research(self, base: Base) -> None:
        if base.faction != "player":
            return
        multipliers = self.research_manager.base_stat_multipliers(base.name)
        base.apply_stat_multipliers(multipliers)

    def _refresh_research_bonuses(self) -> None:
        """Recompute stats for all friendly entities after research completion."""

        for ship in self.ships:
            self._apply_ship_research(ship)
        for base in self.bases:
            self._apply_base_research(base)


def create_initial_world() -> World:
    """Create a simple sandbox world with one planetoid and one Astral Citadel."""
    world = World(width=4000.0, height=4000.0)

    # For the sandbox, assume Shipwright Foundry + Fleet Forge exist/are online.
    world.research_manager.set_facility_online("ShipwrightFoundry", True)
    world.research_manager.set_facility_online("FleetForge", True)
    # TODO: Hook facility online states to actual facility entities once they exist.

    # Pre-complete early nodes so the sandbox can showcase multiple hull classes.
    for node_id in [
        "SF_STRIKE_FUNDAMENTALS_I",
        "SF_ESCORT_DESIGN_I",
        "SF_ADVANCED_STRIKE_DOCTRINE",
        "SF_ESCORT_HEAVY_FRAMES",
        "FF_HEAVY_HULL_FABRICATION",
    ]:
        world.research_manager.force_complete(node_id)

    planetoid = Planetoid(position=(0.0, 0.0), radius=90.0, resource_yield=120)
    world.planetoids.append(planetoid)

    base = Base(position=(160.0, 0.0))
    world.bases.append(base)
    world._apply_base_research(base)

    # Seed a handful of strike/escort ships for visualization tests.
    spearling = Ship(position=(400.0, 120.0), definition=get_ship_definition("Spearling"))
    warden = Ship(position=(520.0, -80.0), definition=get_ship_definition("Warden"))
    iron_halberd = Ship(position=(-280.0, 200.0), definition=get_ship_definition("Iron Halberd"))
    for ship in (spearling, warden, iron_halberd):
        world._apply_ship_research(ship)
        world.ships.append(ship)

    # Spawn a few enemy ships to exercise combat logic.
    enemy_positions = [(-200.0, -120.0), (-360.0, -80.0), (-420.0, 160.0)]
    for idx, pos in enumerate(enemy_positions):
        definition_name = ["Spearling", "Daggerwing", "Sunlance"][idx]
        enemy_ship = Ship(position=pos, definition=get_ship_definition(definition_name), faction="enemy")
        world.ships.append(enemy_ship)

    # Queue a few autonomous builds so the production loop is observable.
    for ship_name in ["Spearling", "Wisp", "Sunlance"]:
        world.queue_ship(base, ship_name)

    return world


def _spawn_ring_position(center: Vec2, index: int, radius: float = 220.0) -> Vec2:
    angle = math.radians((index % 12) * (360.0 / 12))
    return (
        center[0] + math.cos(angle) * radius,
        center[1] + math.sin(angle) * radius,
    )
