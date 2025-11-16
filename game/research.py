"""Facility-gated research data and progression helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple


FacilityType = str


@dataclass(frozen=True)
class StatBonus:
    """Structured representation of a multiplicative stat modifier.

    Scope semantics (``scope`` field):
    * ``"ship_class"`` – applies to every ship belonging to ``target`` (e.g., ``"Strike"``).
    * ``"all_ships"`` – applies fleet-wide regardless of hull class (``target`` ignored).
    * ``"base"`` – applies to the Astral Citadel / bases (``target`` indicates which base stat).
    * ``"facility"`` – applies to facilities/modules (``target`` unused for now).
    * ``"economy"`` – applies to global economy levers (planetoid/asteroid income, etc.).

    ``amount`` is expressed as a decimal percentage (``0.10`` = +10%).
    ``attribute`` identifies the stat being modified (e.g., ``"shields"``).
    ``description`` paraphrases the design intent for future UI surfacing.
    """

    scope: str
    target: str
    attribute: str
    amount: float
    description: str


@dataclass(frozen=True)
class ResearchNode:
    """Canonical representation of a single research node from guidance."""

    id: str
    name: str
    tree: str
    tier: int
    host_facility_type: FacilityType
    resource_cost: int
    research_time: float
    prerequisites: Tuple[str, ...]
    unlocks_ships: Tuple[str, ...] = field(default_factory=tuple)
    stat_bonuses: Tuple[StatBonus, ...] = field(default_factory=tuple)
    description: str = ""


@dataclass
class ResearchProgress:
    """Tracks a node currently being researched."""

    node_id: str
    remaining_time: float
    paused: bool = False


class ResearchManager:
    """Runtime controller for research availability, progress, and facilities."""

    def __init__(self) -> None:
        self._nodes: Dict[str, ResearchNode] = _build_node_registry()
        self._completed: List[str] = []
        self._active: Optional[ResearchProgress] = None
        # Track facility availability; default False until explicitly brought online.
        self._facilities: Dict[FacilityType, bool] = {
            "ShipwrightFoundry": False,
            "FleetForge": False,
            "ResearchNexus": False,
            "DefenseGridNode": False,
        }

    # ------------------------------------------------------------------
    # Facility state helpers
    # ------------------------------------------------------------------
    def set_facility_online(self, facility_type: FacilityType, online: bool) -> None:
        """Update facility state and pause/resume research as required."""

        self._facilities[facility_type] = online
        if (
            self._active is not None
            and self._nodes[self._active.node_id].host_facility_type == facility_type
        ):
            self._active.paused = not online

    def facility_online(self, facility_type: FacilityType) -> bool:
        return self._facilities.get(facility_type, False)

    # ------------------------------------------------------------------
    # Research lifecycle
    # ------------------------------------------------------------------
    def update(self, dt: float) -> Optional[ResearchNode]:
        """Advance the active research timer, returning completed nodes."""

        if self._active is None:
            return None

        node = self._nodes[self._active.node_id]
        if not self.facility_online(node.host_facility_type):
            self._active.paused = True
            return None

        self._active.paused = False
        self._active.remaining_time -= dt
        if self._active.remaining_time > 0.0:
            return None

        # Research finished.
        self._completed.append(node.id)
        self._active = None
        return node

    def can_start(self, node_id: str, *, available_resources: float) -> bool:
        if node_id not in self._nodes:
            return False
        if node_id in self._completed:
            return False
        if self._active is not None:
            return False
        node = self._nodes[node_id]
        if available_resources < node.resource_cost:
            return False
        if not self.facility_online(node.host_facility_type):
            return False
        return all(prereq in self._completed for prereq in node.prerequisites)

    def start(self, node_id: str, *, available_resources: float) -> bool:
        """Begin researching ``node_id`` if all conditions are satisfied."""

        if not self.can_start(node_id, available_resources=available_resources):
            return False
        node = self._nodes[node_id]
        self._active = ResearchProgress(node_id=node_id, remaining_time=node.research_time)
        return True

    def force_complete(self, node_id: str) -> None:
        """Mark ``node_id`` as finished (used for scenario setup)."""

        if node_id not in self._nodes:
            raise KeyError(f"Unknown research node: {node_id}")
        if node_id not in self._completed:
            self._completed.append(node_id)
        if self._active is not None and self._active.node_id == node_id:
            self._active = None

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def nodes(self) -> Iterable[ResearchNode]:
        return self._nodes.values()

    def completed_nodes(self) -> Tuple[str, ...]:
        return tuple(self._completed)

    def active_node(self) -> Optional[ResearchNode]:
        if self._active is None:
            return None
        return self._nodes[self._active.node_id]

    def available_nodes(self, *, available_resources: float) -> List[ResearchNode]:
        """Return nodes that are ready to start given current state."""

        candidates: List[ResearchNode] = []
        if self._active is not None:
            return candidates
        for node in self._nodes.values():
            if node.id in self._completed:
                continue
            if not self.facility_online(node.host_facility_type):
                continue
            if available_resources < node.resource_cost:
                continue
            if all(prereq in self._completed for prereq in node.prerequisites):
                candidates.append(node)
        return candidates

    def is_ship_unlocked(self, ship_name: str) -> bool:
        """Check if research has unlocked ``ship_name`` (ships with no node stay available)."""

        linked_nodes = [node for node in self._nodes.values() if ship_name in node.unlocks_ships]
        if not linked_nodes:
            # No research requirement defined.
            return True
        return any(node.id in self._completed for node in linked_nodes)


# ----------------------------------------------------------------------
# Canonical node registry sourced from `research_guidance`.
# ----------------------------------------------------------------------
def _build_node_registry() -> Dict[str, ResearchNode]:
    nodes: Dict[str, ResearchNode] = {}
    _register_shipwright_foundry(nodes)
    _register_fleet_forge(nodes)
    _register_research_nexus(nodes)
    _register_defense_grid(nodes)
    return nodes


def _register_shipwright_foundry(nodes: Dict[str, ResearchNode]) -> None:
    tree = "Shipwright Foundry"
    facility = "ShipwrightFoundry"
    nodes["SF_STRIKE_FUNDAMENTALS_I"] = ResearchNode(
        id="SF_STRIKE_FUNDAMENTALS_I",
        name="Strike Fundamentals I",
        tree=tree,
        tier=1,
        host_facility_type=facility,
        resource_cost=1000,
        research_time=20.0,
        prerequisites=(),
        unlocks_ships=("Spearling", "Wisp"),
        description="Baseline Strike hull fabrication patterns (Spearling/Wisp).",
    )
    nodes["SF_ESCORT_DESIGN_I"] = ResearchNode(
        id="SF_ESCORT_DESIGN_I",
        name="Escort Design Principles I",
        tree=tree,
        tier=1,
        host_facility_type=facility,
        resource_cost=2500,
        research_time=40.0,
        prerequisites=("SF_STRIKE_FUNDAMENTALS_I",),
        unlocks_ships=("Warden",),
        description="Unlocks early escort hull architecture (Warden).",
    )
    nodes["SF_ADVANCED_STRIKE_DOCTRINE"] = ResearchNode(
        id="SF_ADVANCED_STRIKE_DOCTRINE",
        name="Advanced Strike Doctrine",
        tree=tree,
        tier=2,
        host_facility_type=facility,
        resource_cost=3000,
        research_time=45.0,
        prerequisites=("SF_STRIKE_FUNDAMENTALS_I",),
        unlocks_ships=("Daggerwing",),
        stat_bonuses=(
            StatBonus(
                scope="ship_class",
                target="Strike",
                attribute="flight_speed",
                amount=0.07,
                description="Global Strike Speed I (+7% flight speed)",
            ),
            StatBonus(
                scope="ship_class",
                target="Strike",
                attribute="firing_range",
                amount=0.05,
                description="Global Strike Firing Range I (+5% firing range)",
            ),
        ),
        description="Advances Strike tactics for heavier raid craft.",
    )
    nodes["SF_ESCORT_HEAVY_FRAMES"] = ResearchNode(
        id="SF_ESCORT_HEAVY_FRAMES",
        name="Escort Heavy Frames",
        tree=tree,
        tier=2,
        host_facility_type=facility,
        resource_cost=4000,
        research_time=60.0,
        prerequisites=("SF_ESCORT_DESIGN_I",),
        unlocks_ships=("Sunlance", "Auric Veil"),
        stat_bonuses=(
            StatBonus(
                scope="ship_class",
                target="Escort",
                attribute="health",
                amount=0.08,
                description="Global Escort Hull I (+8% health)",
            ),
            StatBonus(
                scope="ship_class",
                target="Escort",
                attribute="armor",
                amount=0.05,
                description="Global Escort Hull I (+5% armor)",
            ),
        ),
        description="Enables heavy escort variants and sturdier frames.",
    )
    nodes["SF_STRIKE_WEAPON_OPT_I"] = ResearchNode(
        id="SF_STRIKE_WEAPON_OPT_I",
        name="Strike Weapon Optimization I",
        tree=tree,
        tier=3,
        host_facility_type=facility,
        resource_cost=3500,
        research_time=55.0,
        prerequisites=("SF_ADVANCED_STRIKE_DOCTRINE",),
        stat_bonuses=(
            StatBonus(
                scope="ship_class",
                target="Strike",
                attribute="weapon_damage",
                amount=0.10,
                description="Strike Weapon Damage +10%",
            ),
            StatBonus(
                scope="ship_class",
                target="Strike",
                attribute="energy_regen",
                amount=0.05,
                description="Strike Energy Regen +5%",
            ),
        ),
        description="Refines Strike firing solutions and energy routing.",
    )


def _register_fleet_forge(nodes: Dict[str, ResearchNode]) -> None:
    tree = "Fleet Forge"
    facility = "FleetForge"
    nodes["FF_HEAVY_HULL_FABRICATION"] = ResearchNode(
        id="FF_HEAVY_HULL_FABRICATION",
        name="Heavy Hull Fabrication",
        tree=tree,
        tier=1,
        host_facility_type=facility,
        resource_cost=5000,
        research_time=60.0,
        prerequisites=(),
        unlocks_ships=("Iron Halberd",),
        description="Establishes manufacturing for large Line hulls.",
    )
    nodes["FF_FORTRESS_ARCHITECTURE"] = ResearchNode(
        id="FF_FORTRESS_ARCHITECTURE",
        name="Fortress Architecture",
        tree=tree,
        tier=2,
        host_facility_type=facility,
        resource_cost=6000,
        research_time=70.0,
        prerequisites=("FF_HEAVY_HULL_FABRICATION",),
        unlocks_ships=("Star Fortress",),
        stat_bonuses=(
            StatBonus(
                scope="ship_class",
                target="Line",
                attribute="health",
                amount=0.10,
                description="Line Hull Reinforcement I (+10% health)",
            ),
            StatBonus(
                scope="ship_class",
                target="Line",
                attribute="armor",
                amount=0.10,
                description="Line Hull Reinforcement I (+10% armor)",
            ),
        ),
        description="Unlocks Star Fortress and sturdier Line frames.",
    )
    nodes["FF_LONG_RANGE_PROJECTION"] = ResearchNode(
        id="FF_LONG_RANGE_PROJECTION",
        name="Long-Range Projection Systems",
        tree=tree,
        tier=2,
        host_facility_type=facility,
        resource_cost=6500,
        research_time=75.0,
        prerequisites=("FF_HEAVY_HULL_FABRICATION",),
        unlocks_ships=("Lance of Dawn",),
        stat_bonuses=(
            StatBonus(
                scope="ship_class",
                target="Line",
                attribute="firing_range",
                amount=0.12,
                description="Line Firing Range I (+12% range)",
            ),
        ),
        description="Advanced beam focusing for long-range combat.",
    )
    nodes["FF_CAPITAL_KEEL_ASSEMBLY"] = ResearchNode(
        id="FF_CAPITAL_KEEL_ASSEMBLY",
        name="Capital Keel Assembly",
        tree=tree,
        tier=3,
        host_facility_type=facility,
        resource_cost=9000,
        research_time=90.0,
        prerequisites=("FF_FORTRESS_ARCHITECTURE",),
        unlocks_ships=("Titan's Ward",),
        description="Capital-class keel and command core production.",
    )
    nodes["FF_CROWN_YARDS"] = ResearchNode(
        id="FF_CROWN_YARDS",
        name="Crown-Class Yard Expansion",
        tree=tree,
        tier=3,
        host_facility_type=facility,
        resource_cost=10_000,
        research_time=100.0,
        prerequisites=("FF_CAPITAL_KEEL_ASSEMBLY", "FF_LONG_RANGE_PROJECTION"),
        unlocks_ships=("Abyssal Crown",),
        description="Scales the yards for carrier-grade construction.",
    )
    nodes["FF_SPIRE_BLACKWORKS"] = ResearchNode(
        id="FF_SPIRE_BLACKWORKS",
        name="Spire-Class Blackworks",
        tree=tree,
        tier=4,
        host_facility_type=facility,
        resource_cost=12_000,
        research_time=120.0,
        prerequisites=("FF_CROWN_YARDS",),
        unlocks_ships=("Oblivion Spire",),
        stat_bonuses=(
            StatBonus(
                scope="ship_class",
                target="Capital",
                attribute="weapon_damage",
                amount=0.15,
                description="Capital Weapon Systems I (+15% weapon damage)",
            ),
            StatBonus(
                scope="ship_class",
                target="Capital",
                attribute="firing_range",
                amount=0.10,
                description="Capital Weapon Systems I (+10% firing range)",
            ),
        ),
        description="Extreme fabrication tech for Oblivion Spire builds.",
    )


def _register_research_nexus(nodes: Dict[str, ResearchNode]) -> None:
    tree = "Research Nexus"
    facility = "ResearchNexus"
    nodes["RN_SHIELD_THEORY_I"] = ResearchNode(
        id="RN_SHIELD_THEORY_I",
        name="Shield Theory I",
        tree=tree,
        tier=1,
        host_facility_type=facility,
        resource_cost=3000,
        research_time=45.0,
        prerequisites=(),
        stat_bonuses=(
            StatBonus(
                scope="all_ships",
                target="*",
                attribute="shields",
                amount=0.10,
                description="+10% shields for all ships and base",
            ),
        ),
        description="Initial shield dispersion improvements.",
    )
    nodes["RN_SHIELD_THEORY_II"] = ResearchNode(
        id="RN_SHIELD_THEORY_II",
        name="Shield Theory II",
        tree=tree,
        tier=2,
        host_facility_type=facility,
        resource_cost=4500,
        research_time=60.0,
        prerequisites=("RN_SHIELD_THEORY_I",),
        stat_bonuses=(
            StatBonus(
                scope="all_ships",
                target="*",
                attribute="shields",
                amount=0.15,
                description="Additional +15% shields fleet-wide",
            ),
            StatBonus(
                scope="all_ships",
                target="*",
                attribute="energy_regen",
                amount=0.05,
                description="+5% shield regen (modeled via energy)",
            ),
        ),
        description="Advanced harmonics for shield resilience.",
    )
    nodes["RN_WEAPON_OPTIMIZATION_I"] = ResearchNode(
        id="RN_WEAPON_OPTIMIZATION_I",
        name="Weapon Optimization I",
        tree=tree,
        tier=1,
        host_facility_type=facility,
        resource_cost=3500,
        research_time=50.0,
        prerequisites=(),
        stat_bonuses=(
            StatBonus(
                scope="all_ships",
                target="*",
                attribute="weapon_damage",
                amount=0.08,
                description="+8% weapon damage for all ships",
            ),
            StatBonus(
                scope="all_ships",
                target="*",
                attribute="firing_range",
                amount=0.05,
                description="+5% firing range for all ships",
            ),
        ),
        description="General improvements to fleet weapons.",
    )
    nodes["RN_ENGINE_OVERHAUL_I"] = ResearchNode(
        id="RN_ENGINE_OVERHAUL_I",
        name="Engine Overhaul I",
        tree=tree,
        tier=1,
        host_facility_type=facility,
        resource_cost=3200,
        research_time=45.0,
        prerequisites=(),
        stat_bonuses=(
            StatBonus(
                scope="all_ships",
                target="*",
                attribute="flight_speed",
                amount=0.08,
                description="+8% flight speed fleet-wide",
            ),
            StatBonus(
                scope="all_ships",
                target="*",
                attribute="energy_regen",
                amount=0.05,
                description="+5% energy regen fleet-wide",
            ),
        ),
        description="Drive efficiency improvements.",
    )
    nodes["RN_SENSOR_INTEGRATION_I"] = ResearchNode(
        id="RN_SENSOR_INTEGRATION_I",
        name="Sensor Integration I",
        tree=tree,
        tier=2,
        host_facility_type=facility,
        resource_cost=4000,
        research_time=55.0,
        prerequisites=("RN_ENGINE_OVERHAUL_I",),
        stat_bonuses=(
            StatBonus(
                scope="all_ships",
                target="*",
                attribute="visual_range",
                amount=0.12,
                description="+12% visual range for ships/bases",
            ),
            StatBonus(
                scope="all_ships",
                target="*",
                attribute="radar_range",
                amount=0.15,
                description="+15% radar range for ships/bases",
            ),
        ),
        description="Harmonizes fleet sensor networks.",
    )
    nodes["RN_ECON_THROUGHPUT_I"] = ResearchNode(
        id="RN_ECON_THROUGHPUT_I",
        name="Economic Throughput I",
        tree=tree,
        tier=2,
        host_facility_type=facility,
        resource_cost=5000,
        research_time=70.0,
        prerequisites=("RN_SHIELD_THEORY_I",),
        stat_bonuses=(
            StatBonus(
                scope="economy",
                target="planetoid_income",
                attribute="resource_rate",
                amount=0.10,
                description="+10% planetoid mining output",
            ),
            StatBonus(
                scope="economy",
                target="asteroid_income",
                attribute="resource_rate",
                amount=0.05,
                description="+5% asteroid mining output",
            ),
        ),
        description="Mining/refining throughput upgrades.",
    )


def _register_defense_grid(nodes: Dict[str, ResearchNode]) -> None:
    tree = "Defense Grid Node"
    facility = "DefenseGridNode"
    nodes["DG_STATION_HARDENING_I"] = ResearchNode(
        id="DG_STATION_HARDENING_I",
        name="Station Hardening I",
        tree=tree,
        tier=1,
        host_facility_type=facility,
        resource_cost=3000,
        research_time=45.0,
        prerequisites=(),
        stat_bonuses=(
            StatBonus(
                scope="base",
                target="Astral Citadel",
                attribute="health",
                amount=0.12,
                description="+12% base health",
            ),
            StatBonus(
                scope="base",
                target="Astral Citadel",
                attribute="armor",
                amount=0.10,
                description="+10% base armor",
            ),
            StatBonus(
                scope="facility",
                target="*",
                attribute="health",
                amount=0.10,
                description="+10% facility health",
            ),
        ),
        description="Structural reinforcement for bases/facilities.",
    )
    nodes["DG_ADAPTIVE_DEFENSE_ARRAYS"] = ResearchNode(
        id="DG_ADAPTIVE_DEFENSE_ARRAYS",
        name="Adaptive Defense Arrays",
        tree=tree,
        tier=2,
        host_facility_type=facility,
        resource_cost=4500,
        research_time=60.0,
        prerequisites=("DG_STATION_HARDENING_I",),
        stat_bonuses=(
            StatBonus(
                scope="base",
                target="Astral Citadel",
                attribute="weapon_damage",
                amount=0.15,
                description="+15% base weapon damage",
            ),
            StatBonus(
                scope="base",
                target="Astral Citadel",
                attribute="firing_range",
                amount=0.10,
                description="+10% base firing range",
            ),
        ),
        description="Improves defense battery targeting algorithms.",
    )
    nodes["DG_DEEP_SPACE_GRID"] = ResearchNode(
        id="DG_DEEP_SPACE_GRID",
        name="Deep Space Grid",
        tree=tree,
        tier=3,
        host_facility_type=facility,
        resource_cost=5500,
        research_time=75.0,
        prerequisites=("DG_STATION_HARDENING_I", "RN_SENSOR_INTEGRATION_I"),
        stat_bonuses=(
            StatBonus(
                scope="base",
                target="Astral Citadel",
                attribute="radar_range",
                amount=0.20,
                description="+20% base/facility radar range",
            ),
        ),
        description="Extends long-range detection grids.",
    )
    nodes["DG_EMERGENCY_REPAIR_PROTOCOLS"] = ResearchNode(
        id="DG_EMERGENCY_REPAIR_PROTOCOLS",
        name="Emergency Repair Protocols",
        tree=tree,
        tier=3,
        host_facility_type=facility,
        resource_cost=5000,
        research_time=70.0,
        prerequisites=("DG_STATION_HARDENING_I",),
        stat_bonuses=(),
        description=(
            "Unlocks passive base/facility repair routines (TODO: model actual regen behavior)."
        ),
    )


# TODO: integrate stat bonuses with ship/base attribute calculations once the broader
# systems for modifiers exist. For now, the research manager simply tracks completed
# nodes, facility gating, and ship unlock availability.
