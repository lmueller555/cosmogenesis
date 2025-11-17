"""Canonical facility definitions sourced from `game_guidance`."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class FacilityDefinition:
    """Immutable data describing a buildable facility/module."""

    facility_type: str
    name: str
    description: str
    resource_cost: int
    build_time: float
    health: int
    shields: int


_FACILITIES: Dict[str, FacilityDefinition] = {
    # TODO: Replace placeholder stats with the authoritative numbers from ship/facility specs.
    "ShipwrightFoundry": FacilityDefinition(
        facility_type="ShipwrightFoundry",
        name="Shipwright Foundry",
        description=(
            "Unlocks Strike/Escort hull research trees and enables light ship fabrication."
        ),
        resource_cost=600,
        build_time=45.0,
        health=8000,
        shields=4000,
    ),
    "FleetForge": FacilityDefinition(
        facility_type="FleetForge",
        name="Fleet Forge",
        description=(
            "Supports Line/Capital hull research plus heavy ship fabrication throughput."
        ),
        resource_cost=900,
        build_time=60.0,
        health=11000,
        shields=5500,
    ),
    "ResearchNexus": FacilityDefinition(
        facility_type="ResearchNexus",
        name="Research Nexus",
        description=(
            "Coordinates global upgrades, sensor tech, and economic improvements."
        ),
        resource_cost=700,
        build_time=50.0,
        health=6500,
        shields=5000,
    ),
    "DefenseGridNode": FacilityDefinition(
        facility_type="DefenseGridNode",
        name="Defense Grid Node",
        description=(
            "Projects defensive auras and unlocks station hardening technologies."
        ),
        resource_cost=650,
        build_time=48.0,
        health=7500,
        shields=4200,
    ),
}


def get_facility_definition(facility_type: str) -> FacilityDefinition:
    """Look up a facility definition by its canonical type string."""

    if facility_type not in _FACILITIES:
        raise KeyError(f"Unknown facility type: {facility_type}")
    return _FACILITIES[facility_type]


def all_facility_definitions() -> Iterable[FacilityDefinition]:
    """Iterate over every defined facility type."""

    return _FACILITIES.values()

