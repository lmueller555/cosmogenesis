"""Canonical facility definitions per `game_guidance`."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class FacilityDefinition:
    """Immutable stats for a buildable facility/module."""

    facility_type: str
    display_name: str
    resource_cost: int
    build_time: float
    health: int
    shields: int
    armor: int


# NOTE: Numerical values are placeholders until the human designer supplies
# explicit stats in `game_guidance`. They follow the qualitative guidance that
# facilities have their own resource_cost, build_time, health, and shields.
_FACILITY_DEFINITIONS: Dict[str, FacilityDefinition] = {
    "ShipwrightFoundry": FacilityDefinition(
        facility_type="ShipwrightFoundry",
        display_name="Shipwright Foundry",
        resource_cost=6500,
        build_time=35.0,
        health=15000,
        shields=7000,
        armor=140,
    ),
    "FleetForge": FacilityDefinition(
        facility_type="FleetForge",
        display_name="Fleet Forge",
        resource_cost=9000,
        build_time=48.0,
        health=18500,
        shields=9000,
        armor=180,
    ),
    "ResearchNexus": FacilityDefinition(
        facility_type="ResearchNexus",
        display_name="Research Nexus",
        resource_cost=7200,
        build_time=40.0,
        health=13000,
        shields=8000,
        armor=150,
    ),
    "DefenseGridNode": FacilityDefinition(
        facility_type="DefenseGridNode",
        display_name="Defense Grid Node",
        resource_cost=6000,
        build_time=42.0,
        health=12000,
        shields=8500,
        armor=160,
    ),
}


def get_facility_definition(facility_type: str) -> FacilityDefinition:
    """Return the canonical definition for ``facility_type``."""

    if facility_type not in _FACILITY_DEFINITIONS:
        raise KeyError(f"Unknown facility type: {facility_type}")
    return _FACILITY_DEFINITIONS[facility_type]


def all_facility_definitions() -> Iterable[FacilityDefinition]:
    """Iterate over every known facility definition."""

    return tuple(_FACILITY_DEFINITIONS.values())
