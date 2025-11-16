"""World setup for the Cosmogenesis prototype."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .entities import Base, Facility, Planetoid, Ship
from .ship_registry import (
    ShipDefinition,
    all_ship_definitions,
    get_ship_definition,
)
from .research import ResearchAvailability, ResearchManager, ResearchNode
from .visibility import VisibilityGrid

Vec2 = Tuple[float, float]

# ---------------------------------------------------------------------------
# Production facility requirements derived from `ship_guidance`.
# Strike/Escort hulls are fabricated via Shipwright Foundries; Line/Capital
# hulls demand a Fleet Forge online.
# ---------------------------------------------------------------------------
SHIP_CLASS_PRODUCTION_FACILITY: dict[str, Optional[str]] = {
    "Strike": "ShipwrightFoundry",
    "Escort": "ShipwrightFoundry",
    "Line": "FleetForge",
    "Capital": "FleetForge",
}

FACILITY_DISPLAY_NAMES = {
    "ShipwrightFoundry": "Shipwright Foundry",
    "FleetForge": "Fleet Forge",
    "ResearchNexus": "Research Nexus",
    "DefenseGridNode": "Defense Grid Node",
}


@dataclass
class World:
    width: float
    height: float
    planetoids: List[Planetoid] = field(default_factory=list)
    bases: List[Base] = field(default_factory=list)
    ships: List[Ship] = field(default_factory=list)
    facilities: List[Facility] = field(default_factory=list)
    selected_ships: List[Ship] = field(default_factory=list)
    resources: float = 20_000.0
    resource_income_rate: float = 0.0  # Updated each tick for UI feedback
    research_manager: ResearchManager = field(default_factory=ResearchManager)
    visibility: VisibilityGrid = field(init=False, repr=False)
    player_faction: str = "player"

    # TODO: Extend fog-of-war to account for enemy sensors and neutral factions.

    def __post_init__(self) -> None:
        self.visibility = VisibilityGrid(world_width=self.width, world_height=self.height)

    def update(self, dt: float) -> None:
        """Advance simulation forward by ``dt`` seconds."""

        income_per_second = self._resource_income_per_second()
        self.resource_income_rate = income_per_second
        if income_per_second > 0.0 and dt > 0.0:
            self.resources += income_per_second * dt

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

        self.refresh_visibility()

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

        allowed, _ = self.ship_production_status(base, definition)
        if not allowed:
            return False

        base.queue_ship(ship_name)
        self.resources -= definition.resource_cost
        return True

    def planetoids_controlled_by(self, faction: str) -> List[Planetoid]:
        """Return a list of planetoids currently owned by ``faction``."""

        return [planetoid for planetoid in self.planetoids if planetoid.controller == faction]

    def set_planetoid_controller(self, planetoid: Planetoid, faction: str) -> bool:
        """Assign ``planetoid`` to ``faction``; returns ``True`` if world owns the node."""

        if planetoid not in self.planetoids:
            return False
        planetoid.set_controller(faction)
        return True

    # ------------------------------------------------------------------
    # Facility management (ties into research gating per `research_guidance`).
    # ------------------------------------------------------------------
    def add_facility(self, facility: Facility) -> None:
        """Register ``facility`` and sync the research manager's online state."""

        if facility not in self.facilities:
            self.facilities.append(facility)
        self._sync_facility_type(facility.facility_type)

    def remove_facility(self, facility: Facility) -> None:
        if facility in self.facilities:
            self.facilities.remove(facility)
            self._sync_facility_type(facility.facility_type)

    def set_facility_online(self, facility: Facility, online: bool) -> None:
        if facility not in self.facilities:
            self.facilities.append(facility)
        facility.online = online
        self._sync_facility_type(facility.facility_type)

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

    def ship_production_status(
        self, base: Optional[Base], definition: ShipDefinition
    ) -> Tuple[bool, Optional[str]]:
        """Return whether ``definition`` can currently be queued at ``base``.

        A short status string is provided for UI messaging when construction is
        blocked (insufficient facilities, resources, or research)."""

        if base is None or base not in self.bases or base.faction != self.player_faction:
            return False, "No operational base"

        if not self.research_manager.is_ship_unlocked(definition.name):
            # TODO: Surface the specific research node name once UI affordance exists.
            return False, "Research required"

        facility_type = self._required_facility_for_ship(definition)
        if facility_type is not None and not self._is_facility_online(facility_type):
            friendly_name = FACILITY_DISPLAY_NAMES.get(facility_type, facility_type)
            return False, f"{friendly_name} offline"

        if self.resources < definition.resource_cost:
            shortfall = int(max(0.0, math.ceil(definition.resource_cost - self.resources)))
            if shortfall > 0:
                return False, f"Need {shortfall:,} resources"
            return False, "Insufficient resources"

        return True, None

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

    def research_statuses(self) -> List[ResearchAvailability]:
        """Expose availability summaries for each pending node."""

        return self.research_manager.pending_nodes(available_resources=self.resources)

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

    def _sync_facility_type(self, facility_type: str) -> None:
        """Push current online/offline state for ``facility_type`` to research."""

        online = any(
            facility.online for facility in self.facilities if facility.facility_type == facility_type
        )
        self.research_manager.set_facility_online(facility_type, online)

    def _is_facility_online(self, facility_type: str) -> bool:
        return self.research_manager.facility_online(facility_type)

    def _required_facility_for_ship(self, definition: ShipDefinition) -> Optional[str]:
        return SHIP_CLASS_PRODUCTION_FACILITY.get(definition.ship_class)

    def _resource_income_per_second(self) -> float:
        """Compute the passive resource income for the current tick."""

        if not self.planetoids:
            return 0.0

        controlled_planetoids = self.planetoids_controlled_by(self.player_faction)
        if not controlled_planetoids:
            return 0.0

        planetoid_income = 0.0
        for planetoid in controlled_planetoids:
            # ``resource_yield`` is interpreted as resources per minute per guidance.
            planetoid_income += planetoid.resource_yield / 60.0

        if planetoid_income <= 0.0:
            return 0.0

        bonus = self.research_manager.economy_bonus(
            target="planetoid_income", attribute="resource_rate"
        )
        multiplier = 1.0 + bonus
        return planetoid_income * multiplier

    def refresh_visibility(self) -> None:
        """Rebuild fog-of-war state based on friendly sensors."""

        if not hasattr(self, "visibility"):
            return
        self.visibility.begin_frame()
        for position, visual_range, radar_range in self._visibility_sources():
            if visual_range > 0.0:
                self.visibility.mark_visual(position, visual_range)
            if radar_range > 0.0:
                self.visibility.mark_radar(position, radar_range)

    def _visibility_sources(self) -> List[Tuple[Vec2, float, float]]:
        sources: List[Tuple[Vec2, float, float]] = []
        for base in self.bases:
            if base.faction != "player":
                continue
            sources.append((base.position, base.visual_range_value, base.radar_range_value))
        for ship in self.ships:
            if ship.faction != "player":
                continue
            sources.append((ship.position, ship.visual_range, ship.radar_range))
        return sources


def create_initial_world() -> World:
    """Create a simple sandbox world with one planetoid and one Astral Citadel."""
    world = World(width=4000.0, height=4000.0)

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
    world.set_planetoid_controller(planetoid, world.player_faction)

    base = Base(position=(160.0, 0.0))
    world.bases.append(base)
    world._apply_base_research(base)

    # Stub in Shipwright Foundry + Fleet Forge attached to the Astral Citadel.
    shipwright = Facility(
        position=base.position,
        facility_type="ShipwrightFoundry",
        name="Shipwright Foundry",
        host_base=base,
    )
    fleet_forge = Facility(
        position=base.position,
        facility_type="FleetForge",
        name="Fleet Forge",
        host_base=base,
    )
    world.add_facility(shipwright)
    world.add_facility(fleet_forge)

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

    world.refresh_visibility()

    return world


def _spawn_ring_position(center: Vec2, index: int, radius: float = 220.0) -> Vec2:
    angle = math.radians((index % 12) * (360.0 / 12))
    return (
        center[0] + math.cos(angle) * radius,
        center[1] + math.sin(angle) * radius,
    )
