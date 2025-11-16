"""World setup for the Cosmogenesis prototype."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .ai import EnemyAIController
from .entities import Asteroid, Base, Facility, Planetoid, Ship, WorkerAssignment
from .ship_registry import (
    ShipDefinition,
    all_ship_definitions,
    get_ship_definition,
)
from .facility_registry import (
    FacilityDefinition,
    all_facility_definitions,
    get_facility_definition,
)
from .research import ResearchAvailability, ResearchManager, ResearchNode
from .visibility import VisibilityGrid

Vec2 = Tuple[float, float]
SHIP_COLLISION_PUSH_SPEED = 180.0

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
class BeamVisual:
    """Transient visual representing a beam fired between two ships."""

    start: Vec2
    end: Vec2
    faction: str
    duration: float = 0.35
    age: float = 0.0

    def advance(self, dt: float) -> None:
        if dt > 0.0:
            self.age += dt

    def alpha(self) -> float:
        if self.duration <= 0.0:
            return 0.0
        remaining = max(0.0, 1.0 - self.age / self.duration)
        return min(1.0, remaining)

    def expired(self) -> bool:
        return self.age >= self.duration


@dataclass
class World:
    width: float
    height: float
    planetoids: List[Planetoid] = field(default_factory=list)
    asteroids: List[Asteroid] = field(default_factory=list)
    bases: List[Base] = field(default_factory=list)
    ships: List[Ship] = field(default_factory=list)
    facilities: List[Facility] = field(default_factory=list)
    facility_jobs: List[FacilityConstructionJob] = field(default_factory=list)
    selected_ships: List[Ship] = field(default_factory=list)
    selected_base: Base | None = None
    resources: float = 20_000.0
    resource_income_rate: float = 0.0  # Updated each tick for UI feedback
    research_manager: ResearchManager = field(default_factory=ResearchManager)
    visibility: VisibilityGrid = field(init=False, repr=False)
    player_faction: str = "player"
    enemy_ai: EnemyAIController | None = field(default=None, init=False, repr=False)
    beam_visuals: List[BeamVisual] = field(default_factory=list, repr=False)

    # TODO: Extend fog-of-war to account for enemy sensors and neutral factions.

    def __post_init__(self) -> None:
        self.visibility = VisibilityGrid(world_width=self.width, world_height=self.height)
        self.enemy_ai = EnemyAIController(self)

    def update(self, dt: float) -> None:
        """Advance simulation forward by ``dt`` seconds."""

        passive_rate = self._resource_income_per_second()
        passive_income = passive_rate * dt if dt > 0.0 else 0.0
        total_income = passive_income

        if self.enemy_ai is not None:
            self.enemy_ai.update(dt)

        for ship in self.ships:
            ship.update(dt)
            ship.tick_weapon_cooldown(dt)

        self._resolve_ship_collisions(dt)

        worker_income = self._update_worker_behaviors(dt)
        total_income += worker_income
        self.resources += total_income
        if dt > 0.0:
            instantaneous_rate = total_income / dt
            if self.resource_income_rate <= 0.0:
                self.resource_income_rate = instantaneous_rate
            else:
                self.resource_income_rate = (
                    0.8 * self.resource_income_rate + 0.2 * instantaneous_rate
                )
        else:
            self.resource_income_rate = 0.0

        for base in self.bases:
            completed = base.update(dt)
            for ship_definition in completed:
                self._spawn_ship_from_base(base, ship_definition)

        self._update_facility_construction(dt)
        self._update_combat(dt)
        self._update_beam_visuals(dt)
        completed_research = self.research_manager.update(dt)
        if completed_research is not None:
            # TODO: propagate stat bonuses / notifications once UI exists.
            self._refresh_research_bonuses()

        self.refresh_visibility()

    def issue_move_order(self, destination: Vec2, *, behavior: str = "move") -> None:
        """Send every selected ship toward ``destination``."""

        for ship in self.selected_ships:
            ship.set_move_target(destination, behavior=behavior)

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

    def asteroids_controlled_by(self, faction: str) -> List[Asteroid]:
        """Return every asteroid currently aligned with ``faction``."""

        return [asteroid for asteroid in self.asteroids if asteroid.controller == faction]

    def set_asteroid_controller(self, asteroid: Asteroid, faction: str) -> bool:
        """Assign ``asteroid`` to ``faction`` if it belongs to this world."""

        if asteroid not in self.asteroids:
            return False
        asteroid.set_controller(faction)
        # TODO: Integrate contested capture/combat when mining units exist.
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

    def facilities_for_base(self, base: Optional[Base]) -> List[Facility]:
        """Return facilities filtered to ``base`` (or all when ``None``)."""

        if base is None:
            return list(self.facilities)
        return [facility for facility in self.facilities if facility.host_base == base]

    def facility_display_name(self, facility_type: str) -> str:
        """Return a human-friendly facility name for UI surfaces."""

        return FACILITY_DISPLAY_NAMES.get(facility_type, facility_type)

    def unlocked_ship_definitions(self) -> List[ShipDefinition]:
        """Expose the ship hulls currently unlocked for production."""

        unlocked: List[ShipDefinition] = []
        for definition in all_ship_definitions():
            if self.research_manager.is_ship_unlocked(definition.name):
                unlocked.append(definition)
        return unlocked

    def facilities_for_base(self, base: Base) -> List[Facility]:
        return [facility for facility in self.facilities if facility.host_base == base]

    def facility_jobs_for_base(self, base: Base) -> List[FacilityConstructionJob]:
        return [job for job in self.facility_jobs if job.base == base]

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
            friendly_name = self.facility_display_name(facility_type)
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
        if ship.is_worker:
            self._configure_worker(ship, base)
        self.ships.append(ship)

    def _resolve_ship_collisions(self, dt: float) -> None:
        """Gently push overlapping idle ships apart so they don't fully stack."""

        if dt <= 0.0 or not self.ships:
            return

        colliders: List[Ship] = [
            ship
            for ship in self.ships
            if not ship.is_worker and ship.move_target is None and ship.collision_radius > 0.0
        ]
        if len(colliders) < 2:
            return

        max_push = SHIP_COLLISION_PUSH_SPEED * dt
        for index, ship in enumerate(colliders):
            for other_index in range(index + 1, len(colliders)):
                other = colliders[other_index]
                min_distance = ship.collision_radius + other.collision_radius
                if min_distance <= 0.0:
                    continue
                dx = other.position[0] - ship.position[0]
                dy = other.position[1] - ship.position[1]
                distance = math.hypot(dx, dy)
                if distance >= min_distance:
                    continue
                overlap = min_distance - distance
                if distance <= 1e-5:
                    angle = math.radians((index * 31 + other_index * 17) % 360)
                    direction_x = math.cos(angle)
                    direction_y = math.sin(angle)
                else:
                    direction_x = dx / distance
                    direction_y = dy / distance
                push_distance = min(overlap * 0.5, max_push)
                if push_distance <= 0.0:
                    continue
                ship.position = (
                    ship.position[0] - direction_x * push_distance,
                    ship.position[1] - direction_y * push_distance,
                )
                other.position = (
                    other.position[0] + direction_x * push_distance,
                    other.position[1] + direction_y * push_distance,
                )

    def _update_combat(self, dt: float) -> None:
        """Resolve simplistic auto-attacks between hostile ships."""

        destroyed: List[Ship] = []
        for ship in self.ships:
            if ship.target is None or ship.target not in self.ships or not ship.in_firing_range(ship.target):
                ship.acquire_target(self.ships)
            if ship.target is None:
                ship.hold_position_for_attack(False)
                continue
            if not ship.is_enemy(ship.target):
                ship.clear_target()
                ship.hold_position_for_attack(False)
                continue
            if ship.weapon_damage_value <= 0.0:
                ship.hold_position_for_attack(False)
                continue
            engaged = (
                ship.move_behavior == "attack"
                and ship.move_target is not None
                and ship.target is not None
                and ship.in_firing_range(ship.target)
            )
            ship.hold_position_for_attack(engaged)
            if ship.can_fire():
                target = ship.target
                damage = ship.deal_damage()
                # TODO: Replace with burst fire logic once cadence guidance is available.
                if target is not None and target.apply_damage(damage):
                    destroyed.append(target)
                    ship.clear_target()
                self._spawn_beam_visual(ship, target)

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

    def _spawn_beam_visual(self, attacker: Ship, target: Ship | None) -> None:
        if target is None:
            return
        beam = BeamVisual(
            start=(attacker.position[0], attacker.position[1]),
            end=(target.position[0], target.position[1]),
            faction=attacker.faction,
        )
        self.beam_visuals.append(beam)

    def _update_beam_visuals(self, dt: float) -> None:
        if dt <= 0.0 or not self.beam_visuals:
            return
        active: List[BeamVisual] = []
        for beam in self.beam_visuals:
            beam.advance(dt)
            if not beam.expired():
                active.append(beam)
        self.beam_visuals = active

    def _update_worker_behaviors(self, dt: float) -> float:
        if not self.ships:
            return 0.0
        total_income = 0.0
        for ship in self.ships:
            assignment = ship.worker_assignment
            if assignment is None:
                continue
            base = assignment.home_base
            if base not in self.bases:
                continue
            target = assignment.resource_target
            if getattr(target, "controller", ship.faction) != ship.faction:
                assignment.state = "waiting"
                ship.set_move_target(None)
                continue
            if assignment.state == "waiting":
                assignment.state = "travel_to_node"
                ship.set_move_target(target.position)
            if assignment.state == "travel_to_node":
                if ship.move_target is None:
                    assignment.state = "mining"
                    assignment.mining_timer = max(0.0, assignment.mining_duration)
                continue
            if assignment.state == "mining":
                if assignment.mining_duration <= 0.0:
                    assignment.state = "travel_to_base"
                    assignment.cargo = 0.0
                    ship.set_move_target(base.position)
                    continue
                assignment.mining_timer = max(0.0, assignment.mining_timer - dt)
                if assignment.mining_timer <= 0.0:
                    assignment.state = "travel_to_base"
                    assignment.cargo = self._worker_cargo_amount(ship, assignment)
                    ship.set_move_target(base.position)
                continue
            if assignment.state == "travel_to_base":
                if ship.move_target is None:
                    assignment.state = "depositing"
                continue
            if assignment.state == "depositing":
                delivered = assignment.cargo
                if delivered > 0.0:
                    total_income += delivered
                assignment.cargo = 0.0
                assignment.state = "travel_to_node"
                ship.set_move_target(target.position)
        return total_income

    def _worker_cargo_amount(self, ship: Ship, assignment: WorkerAssignment) -> float:
        target = assignment.resource_target
        base_rate = getattr(target, "resource_yield", 0.0) / 60.0
        harvest = base_rate * max(0.0, assignment.mining_duration)
        capacity = ship.definition.worker_carry_capacity
        if capacity > 0.0:
            harvest = min(harvest, capacity)
        return max(0.0, harvest)

    def _configure_worker(
        self,
        ship: Ship,
        base: Base,
        resource_target: Planetoid | Asteroid | None = None,
    ) -> None:
        if not ship.is_worker:
            return
        target = resource_target or self._default_worker_target(base)
        if target is None:
            return
        assignment = WorkerAssignment(
            home_base=base,
            resource_target=target,
            state="travel_to_node",
            mining_duration=max(0.1, ship.definition.worker_mining_time),
        )
        ship.worker_assignment = assignment
        ship.set_move_target(target.position)

    def _default_worker_target(self, base: Base) -> Planetoid | Asteroid | None:
        owned_planetoids = [
            node for node in self.planetoids if node.controller == base.faction
        ]
        if owned_planetoids:
            return min(
                owned_planetoids,
                key=lambda node: (node.position[0] - base.position[0]) ** 2
                + (node.position[1] - base.position[1]) ** 2,
            )
        owned_asteroids = [
            node for node in self.asteroids if node.controller == base.faction
        ]
        if owned_asteroids:
            return min(
                owned_asteroids,
                key=lambda node: (node.position[0] - base.position[0]) ** 2
                + (node.position[1] - base.position[1]) ** 2,
            )
        return None

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

    def has_facility(self, base: Base, facility_type: str) -> bool:
        return any(
            facility.host_base == base and facility.facility_type == facility_type
            for facility in self.facilities
        )

    def facility_under_construction(self, base: Base, facility_type: str) -> bool:
        return any(
            job.base == base and job.definition.facility_type == facility_type
            for job in self.facility_jobs
        )

    def facility_construction_status(
        self, base: Optional[Base], definition: FacilityDefinition
    ) -> Tuple[bool, Optional[str]]:
        if base is None or base not in self.bases or base.faction != self.player_faction:
            return False, "No operational base"
        if self.has_facility(base, definition.facility_type):
            return False, "Already built"
        if self.facility_under_construction(base, definition.facility_type):
            return False, "Under construction"
        if self.resources < definition.resource_cost:
            shortfall = int(max(0.0, math.ceil(definition.resource_cost - self.resources)))
            if shortfall > 0:
                return False, f"Need {shortfall:,} resources"
            return False, "Insufficient resources"
        return True, None

    def queue_facility(self, base: Base, facility_type: str) -> bool:
        """Start constructing ``facility_type`` if resources allow."""

        if base not in self.bases:
            return False
        try:
            definition = get_facility_definition(facility_type)
        except KeyError:
            return False
        allowed, _ = self.facility_construction_status(base, definition)
        if not allowed:
            return False
        job = FacilityConstructionJob(
            base=base,
            definition=definition,
            remaining_time=definition.build_time,
        )
        self.facility_jobs.append(job)
        self.resources -= definition.resource_cost
        return True

    def _resource_income_per_second(self) -> float:
        """Passive income is disabled; workers ferry resources instead."""

        return 0.0

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

    def _update_facility_construction(self, dt: float) -> None:
        if not self.facility_jobs:
            return
        completed: List[FacilityConstructionJob] = []
        for job in list(self.facility_jobs):
            if job.base not in self.bases:
                self.facility_jobs.remove(job)
                continue
            if dt <= 0.0:
                continue
            job.remaining_time -= dt
            if job.remaining_time <= 0.0:
                completed.append(job)
        for job in completed:
            if job in self.facility_jobs:
                self.facility_jobs.remove(job)
            base = job.base
            slot_index = self._next_facility_slot(base)
            position = self._facility_slot_position(base, slot_index)
            facility = Facility(position=position, definition=job.definition, host_base=base)
            self.add_facility(facility)

    def _next_facility_slot(self, base: Base) -> int:
        return sum(1 for facility in self.facilities if facility.host_base == base)

    def _facility_slot_position(self, base: Base, slot_index: int) -> Vec2:
        # TODO: Align facility attachment points with art-directed sockets from game_guidance.
        angle = math.radians((slot_index % 6) * (360.0 / 6.0))
        radius = 180.0 + 25.0 * (slot_index // 6)
        return (
            base.position[0] + math.cos(angle) * radius,
            base.position[1] + math.sin(angle) * radius,
        )


def create_initial_world() -> World:
    """Create a simple sandbox world with one planetoid and one Astral Citadel."""
    world = World(width=4000.0, height=4000.0)

    # Pre-complete early nodes so the sandbox can showcase multiple hull classes.
    for node_id in [
        "SF_STRIKE_FUNDAMENTALS_I",
    ]:
        world.research_manager.force_complete(node_id)

    planetoid = Planetoid(position=(0.0, 0.0), radius=90.0, resource_yield=120)
    world.planetoids.append(planetoid)
    world.set_planetoid_controller(planetoid, world.player_faction)

    asteroid_positions = [(-320.0, 260.0), (280.0, -280.0), (520.0, 140.0)]
    for idx, position in enumerate(asteroid_positions):
        radius = 24.0 + idx * 3.0
        asteroid = Asteroid(position=position, radius=radius, resource_yield=35 + idx * 5)
        world.asteroids.append(asteroid)
        world.set_asteroid_controller(asteroid, world.player_faction)

    base = Base(position=(260.0, 0.0))
    world.bases.append(base)
    world._apply_base_research(base)

    worker_def = get_ship_definition("Skimmer Drone")
    for idx in range(3):
        spawn_pos = _spawn_ring_position(base.position, idx, radius=140.0)
        worker = Ship(position=spawn_pos, definition=worker_def)
        world._apply_ship_research(worker)
        world._configure_worker(worker, base, resource_target=planetoid)
        world.ships.append(worker)

    # Stub in Shipwright Foundry + Fleet Forge attached to the Astral Citadel.
    shipwright_def = get_facility_definition("ShipwrightFoundry")
    fleet_forge_def = get_facility_definition("FleetForge")
    research_nexus_def = get_facility_definition("ResearchNexus")
    shipwright = Facility(
        position=world._facility_slot_position(base, world._next_facility_slot(base)),
        definition=shipwright_def,
        host_base=base,
    )
    research_nexus = Facility(
        position=world._facility_slot_position(base, world._next_facility_slot(base)),
        definition=research_nexus_def,
        host_base=base,
    )
    world.add_facility(shipwright)
    fleet_forge = Facility(
        position=world._facility_slot_position(base, world._next_facility_slot(base)),
        definition=fleet_forge_def,
        host_base=base,
    )
    world.add_facility(fleet_forge)
    world.add_facility(research_nexus)

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

    world.refresh_visibility()

    return world


def _spawn_ring_position(center: Vec2, index: int, radius: float = 220.0) -> Vec2:
    angle = math.radians((index % 12) * (360.0 / 12))
    return (
        center[0] + math.cos(angle) * radius,
        center[1] + math.sin(angle) * radius,
    )
@dataclass
class FacilityConstructionJob:
    base: Base
    definition: FacilityDefinition
    remaining_time: float

