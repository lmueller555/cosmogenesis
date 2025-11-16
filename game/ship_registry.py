"""Canonical ship definitions derived from `ship_guidance`."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class ShipDefinition:
    """Immutable data for a playable ship hull."""

    name: str
    ship_class: str
    role: str
    lore_blurb: str
    resource_cost: int
    build_time: float
    health: int
    armor: int
    shields: int
    energy: int
    energy_regen: float
    flight_speed: float
    visual_range: float
    radar_range: float
    firing_range: float
    weapon_damage: float
    design_notes_wireframe: str
    upgrade_hooks: List[str]


def _strike_definitions() -> Dict[str, ShipDefinition]:
    return {
        "Spearling": ShipDefinition(
            name="Spearling",
            ship_class="Strike",
            role="High-speed interceptor",
            lore_blurb=(
                "Spearlings are the first through the breach and the first to die. "
                "Pilots claim that if you can survive ten sorties in a Spearling, the rest of the war feels slow."
            ),
            resource_cost=1000,
            build_time=20.0,
            health=600,
            armor=40,
            shields=300,
            energy=300,
            energy_regen=8.0,
            flight_speed=310.0,
            visual_range=800.0,
            radar_range=1100.0,
            firing_range=700.0,
            weapon_damage=45.0,
            design_notes_wireframe=(
                "Slender arrowhead: V-shaped prow, swept-back wings, central spine, small forked tail."
            ),
            upgrade_hooks=[
                "Afterburners for temporary speed boosts.",
                "Targeting Suite that improves visual and firing range.",
                "Light Armor Plating for modest durability gains.",
            ],
        ),
        "Wisp": ShipDefinition(
            name="Wisp",
            ship_class="Strike",
            role="Long-range recon / sensor craft",
            lore_blurb=(
                "Wisps are infamous among captains: by the time you see one, it has already mapped your entire fleet and vanished into the dark."
            ),
            resource_cost=900,
            build_time=18.0,
            health=450,
            armor=25,
            shields=250,
            energy=400,
            energy_regen=10.0,
            flight_speed=300.0,
            visual_range=1000.0,
            radar_range=1500.0,
            firing_range=600.0,
            weapon_damage=30.0,
            design_notes_wireframe=(
                "Needle-like hull with tiny antennae at the nose, short mid-body wings, and a small central diamond bulge."
            ),
            upgrade_hooks=[
                "Enhanced Sensors for broader radar coverage.",
                "Ghost Drive stealth bursts.",
                "Data Link aura boosting allied radar range.",
            ],
        ),
        "Daggerwing": ShipDefinition(
            name="Daggerwing",
            ship_class="Strike",
            role="Hit-and-run raider",
            lore_blurb=(
                "Daggerwings earned their name from the way they slice across a front line, leaving only debris where logistics ships used to be."
            ),
            resource_cost=1200,
            build_time=22.0,
            health=700,
            armor=55,
            shields=350,
            energy=350,
            energy_regen=8.0,
            flight_speed=290.0,
            visual_range=850.0,
            radar_range=1150.0,
            firing_range=750.0,
            weapon_damage=60.0,
            design_notes_wireframe=(
                "Broad delta / bat-wing triangle with rear notches and internal lines from nose to wingtips."
            ),
            upgrade_hooks=[
                "Pulsed Overcharger for short-term weapon boosts.",
                "Reinforced Wing Struts for more health/armor.",
                "Raider Doctrine AI tweaks for harassment.",
            ],
        ),
    }


def _escort_definitions() -> Dict[str, ShipDefinition]:
    return {
        "Warden": ShipDefinition(
            name="Warden",
            ship_class="Escort",
            role="Point-defense & escort",
            lore_blurb=(
                "Wardens were originally designed to guard civilian convoys. In wartime, they form a living shield wall around vulnerable capitals and stations."
            ),
            resource_cost=4800,
            build_time=34.0,
            health=3200,
            armor=160,
            shields=2200,
            energy=1200,
            energy_regen=20.0,
            flight_speed=230.0,
            visual_range=900.0,
            radar_range=1300.0,
            firing_range=900.0,
            weapon_damage=95.0,
            design_notes_wireframe=(
                "Compact block with side sponsons, top turret hints, and a central keel line."
            ),
            upgrade_hooks=[
                "Point Defense Array bonus vs small ships.",
                "Bulwark Shields for higher shields but slower speed.",
                "Escort Formation AI synergies when grouped.",
            ],
        ),
        "Sunlance": ShipDefinition(
            name="Sunlance",
            ship_class="Escort",
            role="Assault / general-purpose combatant",
            lore_blurb=(
                "Sunlances earned their reputation burning through pirate flotillas. Their beam arrays were never meant for subtlety."
            ),
            resource_cost=5200,
            build_time=36.0,
            health=3000,
            armor=140,
            shields=2400,
            energy=1500,
            energy_regen=22.0,
            flight_speed=240.0,
            visual_range=950.0,
            radar_range=1350.0,
            firing_range=1000.0,
            weapon_damage=130.0,
            design_notes_wireframe=(
                "Sleek wedge hull with parallel beam spines and a notched rear engine cluster."
            ),
            upgrade_hooks=[
                "Focused Lances for more range/damage.",
                "Flux Sinks to improve energy regen.",
                "Adaptive Plating for moderate durability boosts.",
            ],
        ),
        "Auric Veil": ShipDefinition(
            name="Auric Veil",
            ship_class="Escort",
            role="Support / shield extender",
            lore_blurb=(
                "Auric Veils are named for the shimmering fields they cast across allied hulls. Fleet commanders fight over who gets the few they can afford."
            ),
            resource_cost=5500,
            build_time=38.0,
            health=2600,
            armor=120,
            shields=3200,
            energy=2000,
            energy_regen=28.0,
            flight_speed=220.0,
            visual_range=900.0,
            radar_range=1400.0,
            firing_range=850.0,
            weapon_damage=75.0,
            design_notes_wireframe=(
                "Diamond hull with partial halo arcs above/below connected via short spokes, emphasizing aura/support."
            ),
            upgrade_hooks=[
                "Shield Projectors that buff nearby allies.",
                "Capacitor Banks for larger energy reserves.",
                "Harmonic Field damage reduction aura.",
            ],
        ),
    }


def _line_definitions() -> Dict[str, ShipDefinition]:
    return {
        "Iron Halberd": ShipDefinition(
            name="Iron Halberd",
            ship_class="Line",
            role="Frontline brawler",
            lore_blurb=(
                "The Iron Halberd is an old design that refuses to die, much like the captains who favor it. When it appears on the field, everyone knows the brawl has truly begun."
            ),
            resource_cost=10_000,
            build_time=50.0,
            health=8500,
            armor=320,
            shields=5200,
            energy=2800,
            energy_regen=30.0,
            flight_speed=180.0,
            visual_range=1100.0,
            radar_range=1500.0,
            firing_range=1300.0,
            weapon_damage=230.0,
            design_notes_wireframe=(
                "Long bar hull with forward halberd axe-head, layered side plates, and triple engine lines."
            ),
            upgrade_hooks=[
                "Reinforced Ram for close-assault bonuses.",
                "Citadel Armor for extreme durability at speed cost.",
                "Siege Batteries with higher range/damage but slower cadence.",
            ],
        ),
        "Star Fortress": ShipDefinition(
            name="Star Fortress",
            ship_class="Line",
            role="Defensive anchor / area denial",
            lore_blurb=(
                "The Star Fortress is less a ship and more a mobile wall. When it digs in, sectors change hands around it."
            ),
            resource_cost=11_000,
            build_time=52.0,
            health=9500,
            armor=350,
            shields=6000,
            energy=2600,
            energy_regen=26.0,
            flight_speed=160.0,
            visual_range=1050.0,
            radar_range=1550.0,
            firing_range=1250.0,
            weapon_damage=210.0,
            design_notes_wireframe=(
                "Blocky cross with stubby arms ending in turret squares and internal cross bracing."
            ),
            upgrade_hooks=[
                "Entrench Mode that trades speed for range/armor.",
                "Bastion Shields for temporary huge shield boosts.",
                "Control Grid improving radar and command auras.",
            ],
        ),
        "Lance of Dawn": ShipDefinition(
            name="Lance of Dawn",
            ship_class="Line",
            role="Long-range beam artillery",
            lore_blurb=(
                "When the Lance of Dawn fires, fleets hundreds of kilometers away see the flash and pray it isn’t aimed at them."
            ),
            resource_cost=10_500,
            build_time=50.0,
            health=7800,
            armor=280,
            shields=5000,
            energy=3400,
            energy_regen=34.0,
            flight_speed=175.0,
            visual_range=1200.0,
            radar_range=1700.0,
            firing_range=1450.0,
            weapon_damage=300.0,
            design_notes_wireframe=(
                "Long spear-like hull with a projector ring at the nose and thin stabilizer fins mid-body."
            ),
            upgrade_hooks=[
                "Coherent Lattice for more range/damage.",
                "Focus Crystals enabling charged shots.",
                "Sensor Sync bonuses when paired with recon ships.",
            ],
        ),
    }


def _capital_definitions() -> Dict[str, ShipDefinition]:
    return {
        "Titan's Ward": ShipDefinition(
            name="Titan's Ward",
            ship_class="Capital",
            role="Command ship / super-heavy brawler",
            lore_blurb=(
                "Titan's Wards are named not for any mythical giant, but for the worlds they’ve been credited with saving—or breaking."
            ),
            resource_cost=20_000,
            build_time=75.0,
            health=18_000,
            armor=500,
            shields=12_000,
            energy=6000,
            energy_regen=40.0,
            flight_speed=140.0,
            visual_range=1300.0,
            radar_range=1900.0,
            firing_range=1600.0,
            weapon_damage=420.0,
            design_notes_wireframe=(
                "Massive layered barge with stacked decks, turret ridges, dorsal spine, and broad engine block."
            ),
            upgrade_hooks=[
                "Command Nexus aura upgrades.",
                "Titanic Armor for even more survivability.",
                "Divine Batteries increasing weapon might.",
            ],
        ),
        "Abyssal Crown": ShipDefinition(
            name="Abyssal Crown",
            ship_class="Capital",
            role="Siege carrier",
            lore_blurb=(
                "The Abyssal Crown carries enough hangar space to blot out stars. Its presence above a world usually marks the end of negotiations."
            ),
            resource_cost=21_500,
            build_time=80.0,
            health=16_000,
            armor=420,
            shields=14_000,
            energy=7000,
            energy_regen=46.0,
            flight_speed=130.0,
            visual_range=1350.0,
            radar_range=2000.0,
            firing_range=1700.0,
            weapon_damage=350.0,
            design_notes_wireframe=(
                "Elongated hull encircled by a broken crown ring, hangar notches on the sides, and a forward siege projector."
            ),
            upgrade_hooks=[
                "Expanded Hangars for future strikecraft systems.",
                "Siege Arrays boosting structure damage.",
                "Crown Shielding directional defenses.",
            ],
        ),
        "Oblivion Spire": ShipDefinition(
            name="Oblivion Spire",
            ship_class="Capital",
            role="Doomsday gun platform",
            lore_blurb=(
                "Legend says only three Oblivion Spires were ever completed, and that each one left a trail of dead sectors behind it."
            ),
            resource_cost=23_000,
            build_time=85.0,
            health=17_500,
            armor=480,
            shields=13_000,
            energy=8000,
            energy_regen=50.0,
            flight_speed=120.0,
            visual_range=1400.0,
            radar_range=2100.0,
            firing_range=1850.0,
            weapon_damage=600.0,
            design_notes_wireframe=(
                "Narrow hull with a tall vertical spire ending in an open-frame cage emitter."
            ),
            upgrade_hooks=[
                "Oblivion Charge for devastating shots.",
                "Spire Stabilizers for accuracy.",
                "Void Capacitors expanding energy supply.",
            ],
        ),
    }


SHIP_DEFINITIONS: Dict[str, ShipDefinition] = {}
SHIP_DEFINITIONS.update(_strike_definitions())
SHIP_DEFINITIONS.update(_escort_definitions())
SHIP_DEFINITIONS.update(_line_definitions())
SHIP_DEFINITIONS.update(_capital_definitions())


def get_ship_definition(name: str) -> ShipDefinition:
    """Return the canonical ship definition, raising if unknown."""

    try:
        return SHIP_DEFINITIONS[name]
    except KeyError as exc:  # pragma: no cover - simple guard
        raise KeyError(f"Unknown ship definition: {name}") from exc


def all_ship_definitions() -> Iterable[ShipDefinition]:
    """Convenience helper for iterating over every registered ship."""

    return SHIP_DEFINITIONS.values()
