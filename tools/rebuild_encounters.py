#!/usr/bin/env python3
"""Rebuild WARtool encounter groups from a PokeMMO moddable-resource dump.

Usage:
    python tools/rebuild_encounters.py path/to/dump.zip

The generated website data is written to data/groups.js and data/meta.js.
The loader is deliberately tolerant of control characters found in some client
exports and canonicalizes decorated region/type labels before grouping.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POKEMON_PATH = ROOT / "data" / "pokemon.js"
GROUPS_PATH = ROOT / "data" / "groups.js"
META_PATH = ROOT / "data" / "meta.js"

SEASONS = ("Spring", "Summer", "Autumn", "Winter")
WEEK_BY_SEASON = {
    "Summer": "Week 1 · Aug 1–7",
    "Autumn": "Week 2 · Aug 8–14",
    "Winter": "Week 3 · Aug 15–21",
    "Spring": "Week 4 · Aug 22–28",
}
TIME_FIELDS = (("Morning", "rarity_morning"), ("Day", "rarity_day"), ("Night", "rarity_night"))
TIME_ORDER = {name: index for index, (name, _) in enumerate(TIME_FIELDS)}
KNOWN_TYPES = (
    "Super Rod", "Good Rod", "Old Rod", "Dark Grass", "Sweet Scent",
    "Honey Tree", "Dust Cloud", "Headbutt", "Fishing", "Shadow",
    "Inside", "Grass", "Cave", "Water", "Rocks",
)
FOSSILS = (
    (138, "Kanto", "Cinnabar Island Lab"),
    (140, "Kanto", "Cinnabar Island Lab"),
    (142, "Kanto", "Cinnabar Island Lab"),
    (345, "Hoenn", "Devon Corporation"),
    (347, "Hoenn", "Devon Corporation"),
    (408, "Sinnoh", "Oreburgh Mining Museum"),
    (410, "Sinnoh", "Oreburgh Mining Museum"),
    (564, "Unova", "Nacrene Museum"),
    (566, "Unova", "Nacrene Museum"),
)

# Temporary planning assumption requested by the team: the special Zorua
# 3× horde occupies 5% of the conditional Lostlorn Forest 3× horde pool.
# The disclosed numeric species are rescaled to the remaining 95%, keeping
# the horde block total at 5%. Remove this override once the dump exposes a
# confirmed numeric rate.
ASSUMED_UNKNOWN_HORDE_SHARES = {
    (570, "Lostlorn Forest", "3x Horde"): 0.05,
}

# Shiny-safety hazards derived from the current dump's level-up learnsets.
# A move is flagged only when it can appear among the last four level-up moves
# at one or more levels in the actual wild encounter range.
SELF_KO_MOVES = {
    "Selfdestruct": "Faints after use.",
    "Explosion": "Faints after use.",
    "Memento": "Faints after use.",
    "Healing Wish": "Faints after use.",
    "Lunar Dance": "Faints after use.",
    "Final Gambit": "Faints after use.",
}
RECOIL_MOVES = {
    "Take Down": "Deals recoil damage to the user.",
    "Double-Edge": "Deals recoil damage to the user.",
    "Submission": "Deals recoil damage to the user.",
    "Volt Tackle": "Deals recoil damage to the user.",
    "Flare Blitz": "Deals recoil damage to the user.",
    "Brave Bird": "Deals recoil damage to the user.",
    "Wood Hammer": "Deals recoil damage to the user.",
    "Head Smash": "Deals heavy recoil damage to the user.",
    "Wild Charge": "Deals recoil damage to the user.",
    "Head Charge": "Deals recoil damage to the user.",
    "Jump Kick": "Can take crash damage if the move misses or fails.",
    "Hi Jump Kick": "Can take heavy crash damage if the move misses or fails.",
}
CONFUSION_MOVES = {
    "Thrash": "Can leave the user confused and able to damage itself.",
    "Petal Dance": "Can leave the user confused and able to damage itself.",
    "Outrage": "Can leave the user confused and able to damage itself.",
}
HP_COST_MOVES = {
    "Belly Drum": "Costs half of the user's maximum HP.",
}
SUN_DAMAGE_ABILITIES = {
    "Solar Power": "Loses HP each turn in harsh sunlight.",
    "Dry Skin": "Loses HP each turn in harsh sunlight.",
}
HAZARD_SEVERITY_ORDER = {"critical": 0, "warning": 1}


def load_assignment(path: Path, name: str) -> Any:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"window\.{re.escape(name)}=(.*?);(?:\s*window\.|\s*$)", text, re.S)
    if not match:
        raise RuntimeError(f"Could not read {name} from {path}")
    return json.loads(match.group(1))


def load_dump(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with zipfile.ZipFile(path) as archive:
        raw = archive.read("info/monsters.json")
    # Some current exports contain literal control characters inside unrelated
    # item-name strings. strict=False keeps the useful encounter data readable.
    monsters = json.loads(raw.decode("utf-8"), strict=False)
    if not isinstance(monsters, list) or not monsters:
        raise ValueError("info/monsters.json is empty or invalid")
    return monsters, hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_region(value: Any) -> str:
    text = str(value or "").strip()
    match = re.search(r"\[\s*([^\]]+?)\s*\]", text)
    return match.group(1).strip() if match else text


def canonical_type(value: Any) -> str:
    text = str(value or "")
    for known in KNOWN_TYPES:
        if text.endswith(known):
            return known
    return "".join(char for char in text if ord(char) >= 32).strip()


def parse_percent(value: Any) -> float | None:
    if isinstance(value, str) and value.endswith("%"):
        try:
            return float(value[:-1]) / 100.0
        except ValueError:
            return None
    return None


def possible_wild_moves(monster: dict[str, Any], min_level: int, max_level: int) -> dict[str, list[int]]:
    """Return move -> wild levels where it can be in the last-four level-up set."""
    level_moves = sorted([
        (int(move.get("level", 0)), order, str(move.get("name", "")))
        for order, move in enumerate(monster.get("moves", []))
        if move.get("type") == "level" and move.get("name")
    ], key=lambda item: (item[0], item[1]))
    possible: dict[str, list[int]] = collections.defaultdict(list)
    for level in range(max(1, min_level), max(max_level, min_level) + 1):
        known: list[str] = []
        for learn_level, _order, name in level_moves:
            if learn_level > level:
                continue
            # Re-learning the same move makes it the newest entry without
            # occupying two move slots.
            known = [known_move for known_move in known if known_move != name]
            known.append(name)
        for name in known[-4:]:
            possible[name].append(level)
    return possible


def hazard_level_label(min_level: int, max_level: int) -> str:
    return f"Lv. {min_level}" if min_level == max_level else f"Lv. {min_level}–{max_level}"


def hazards_for(monster: dict[str, Any], location: dict[str, Any], method: str) -> list[dict[str, Any]]:
    min_level = int(location.get("min_level") or 1)
    max_level = int(location.get("max_level") or min_level)
    pokemon_id = int(monster["id"])
    pokemon_name = str(monster["name"])
    abilities = sorted({
        str(ability.get("name"))
        for ability in monster.get("abilities", [])
        if ability.get("name") not in {None, "--"}
    })
    types = {str(value).upper() for value in monster.get("types", [])}
    moves = possible_wild_moves(monster, min_level, max_level)
    hazards: list[dict[str, Any]] = []

    def add_move(name: str, severity: str, kind: str, message: str) -> None:
        levels = moves.get(name)
        if not levels:
            return
        level_min, level_max = min(levels), max(levels)
        advice = ""
        if name in {"Selfdestruct", "Explosion"}:
            advice = "Damp or Imprison can block it."
            if "Reactive Gas" in abilities:
                advice = "Reactive Gas can suppress Damp; Imprison is safer."
        elif name == "Memento":
            advice = "Imprison is the safest counter."
        elif name == "Final Gambit":
            advice = "A Ghost-type is immune to Final Gambit."
        if name in RECOIL_MOVES and "Reckless" in abilities:
            advice = "Reckless can increase the recoil damage."
        hazards.append({
            "pokemonId": pokemon_id, "pokemon": pokemon_name,
            "severity": severity, "kind": kind, "source": "move", "name": name,
            "message": message, "advice": advice,
            "levelMin": level_min, "levelMax": level_max,
            "levelLabel": hazard_level_label(level_min, level_max),
        })

    for name, message in SELF_KO_MOVES.items():
        add_move(name, "critical", "self-ko", message)
    for name, message in RECOIL_MOVES.items():
        add_move(name, "warning", "recoil", message)
    for name, message in CONFUSION_MOVES.items():
        add_move(name, "warning", "confusion", message)
    for name, message in HP_COST_MOVES.items():
        add_move(name, "warning", "hp-loss", message)
    if "GHOST" in types:
        add_move("Curse", "warning", "hp-loss", "Ghost-type Curse costs half of the user's maximum HP.")
    # PokeMMO intentionally makes horde members immune to Perish Song. Keep
    # the warning for non-horde encounters only.
    if "Horde" not in method:
        add_move("Perish Song", "critical", "delayed-ko", "Can make the user faint after the perish count expires.")

    for ability_name, message in SUN_DAMAGE_ABILITIES.items():
        if ability_name not in abilities:
            continue
        hazards.append({
            "pokemonId": pokemon_id, "pokemon": pokemon_name,
            "severity": "warning", "kind": "weather", "source": "ability",
            "name": ability_name, "message": message,
            "advice": "Only dangerous when harsh sunlight is active.",
            "levelMin": min_level, "levelMax": max_level,
            "levelLabel": hazard_level_label(min_level, max_level),
        })

    hazards.sort(key=lambda item: (
        HAZARD_SEVERITY_ORDER.get(item["severity"], 9), item["pokemon"], item["source"], item["name"]
    ))
    return hazards


def merge_hazards(hazards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    for hazard in hazards:
        key = (
            int(hazard["pokemonId"]), hazard["severity"], hazard["kind"],
            hazard["source"], hazard["name"], hazard["message"], hazard.get("advice", ""),
        )
        if key not in merged:
            merged[key] = copy.deepcopy(hazard)
            merged[key]["locations"] = list(hazard.get("locations", []))
        else:
            item = merged[key]
            item["levelMin"] = min(int(item["levelMin"]), int(hazard["levelMin"]))
            item["levelMax"] = max(int(item["levelMax"]), int(hazard["levelMax"]))
            item["levelLabel"] = hazard_level_label(item["levelMin"], item["levelMax"])
            item["locations"] = sorted(set(item.get("locations", [])) | set(hazard.get("locations", [])))
    return sorted(merged.values(), key=lambda item: (
        HAZARD_SEVERITY_ORDER.get(item["severity"], 9), item["pokemon"], item["source"], item["name"]
    ))


def refresh_group_hazards(group: dict[str, Any]) -> None:
    location_hazards: list[dict[str, Any]] = []
    for location in group.get("locations", []):
        clean = merge_hazards(list(location.get("hazards", [])))
        location["hazards"] = clean
        label = f"{location.get('region', '')} · {location.get('location', '')}".strip(" ·")
        for hazard in clean:
            item = copy.deepcopy(hazard)
            item["locations"] = [label] if label else []
            location_hazards.append(item)
    group["hazards"] = merge_hazards(location_hazards)
    group["hazardSeverity"] = (
        "critical" if any(item["severity"] == "critical" for item in group["hazards"])
        else "warning" if group["hazards"] else ""
    )
    by_species: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for hazard in group["hazards"]:
        by_species[int(hazard["pokemonId"])].append(hazard)
    for component in group.get("components", []):
        component["hazards"] = copy.deepcopy(by_species.get(int(component["pokemonId"]), []))


def merge_location_details(target: dict[str, Any], source: dict[str, Any]) -> None:
    target["encounterTypes"] = sorted(set(target.get("encounterTypes", [])) | set(source.get("encounterTypes", [])))
    target["levelMin"] = min(int(target.get("levelMin", source.get("levelMin", 1))), int(source.get("levelMin", target.get("levelMin", 1))))
    target["levelMax"] = max(int(target.get("levelMax", source.get("levelMax", 1))), int(source.get("levelMax", target.get("levelMax", 1))))
    target["hazards"] = merge_hazards(list(target.get("hazards", [])) + list(source.get("hazards", [])))


def is_safari(location: dict[str, Any]) -> bool:
    text = f"{location.get('location_name_full', '')} {location.get('location_name', '')}".lower()
    # The Johto Safari Zone Gate is an ordinary map, not a Safari encounter area.
    if "safari zone gate" in text:
        return False
    return "safari zone" in text or "great marsh" in text


def classify_method(location: dict[str, Any]) -> str | None:
    if location.get("is_horde_5x"):
        return "5x Horde"
    if location.get("is_horde_3x"):
        return "3x Horde"
    if is_safari(location):
        return "Safari Singles"
    encounter_type = canonical_type(location.get("type"))
    if encounter_type in {"Grass", "Cave", "Inside", "Water", "Dark Grass"}:
        return "Singles"
    if encounter_type in {"Old Rod", "Good Rod", "Super Rod"}:
        return "Fishing"
    if encounter_type == "Rocks":
        return "Rock Smash"
    if encounter_type == "Headbutt":
        return "Headbutt"
    return None


def component_key(components: list[dict[str, Any]]) -> tuple[Any, ...]:
    return tuple(
        (
            int(item["pokemonId"]), round(float(item["share"]), 12),
            int(item["tier"]), int(item["points"]), item["line"],
            bool(item.get("lureExclusive")),
        )
        for item in components
    )


def build_raw_groups(
    monsters: list[dict[str, Any]], pokemon_by_id: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    numeric: dict[tuple[Any, ...], list[tuple[float, dict[str, Any], dict[str, Any], str]]] = collections.defaultdict(list)
    assumed_unknown: dict[tuple[Any, ...], list[tuple[float, dict[str, Any], dict[str, Any], str]]] = collections.defaultdict(list)
    lure: dict[tuple[Any, ...], list[tuple[dict[str, Any], dict[str, Any]]]] = collections.defaultdict(list)
    monster_by_id = {int(monster["id"]): monster for monster in monsters}

    for monster in monsters:
        pokemon_id = int(monster["id"])
        pokemon = pokemon_by_id.get(pokemon_id)
        if pokemon is None:
            continue
        for original in monster.get("locations", []):
            location = dict(original)
            location["region_name"] = canonical_region(location.get("region_name"))
            location["type"] = canonical_type(location.get("type"))
            method = classify_method(location)
            if method is None:
                continue
            seasons = SEASONS if location.get("season") == "Any" else (location.get("season"),)
            for season in seasons:
                for time_name, field in TIME_FIELDS:
                    value = location.get(field)
                    base_key = (
                        location["region_name"], int(location["location_id"]),
                        location["location_name_full"], location["type"], season, time_name,
                    )
                    key = base_key + (
                        bool(location.get("is_horde_3x")), bool(location.get("is_horde_5x")),
                        int(location.get("rarity_flags", 0)),
                    )
                    component = {
                        "pokemonId": pokemon_id,
                        "pokemon": monster["name"],
                        "tier": int(pokemon["tier"]),
                        "points": int(pokemon["points"]),
                        "line": pokemon["line"],
                        "lureExclusive": False,
                        "rawRate": 0.0,
                    }
                    probability = parse_percent(value)
                    if probability is not None:
                        numeric[key].append((probability, component, location, method))
                    elif value == "Lure":
                        lure[base_key].append((component, location))
                    else:
                        assumed_share = ASSUMED_UNKNOWN_HORDE_SHARES.get(
                            (pokemon_id, location["location_name_full"], method)
                        )
                        if assumed_share is not None:
                            assumed_unknown[key].append((assumed_share, component, location, method))

    rows: list[dict[str, Any]] = []
    for key in sorted(set(numeric) | set(assumed_unknown), key=str):
        entries = list(numeric.get(key, []))
        assumed_entries = list(assumed_unknown.get(key, []))
        region, location_id, location_name, encounter_type, season, time_name, horde_3x, horde_5x, _flags = key
        sample = entries[0] if entries else assumed_entries[0]
        method = sample[3]
        disclosed_total = sum(entry[0] for entry in entries)
        assumed_share_total = sum(entry[0] for entry in assumed_entries)
        if assumed_share_total >= 1.0:
            raise ValueError(f"Assumed shares total {assumed_share_total:.2%} for {key}")
        raw_total = disclosed_total if disclosed_total > 0 else (0.05 if method in {"3x Horde", "5x Horde"} else 1.0)
        if raw_total <= 0:
            continue

        by_species: dict[int, dict[str, Any]] = {}
        disclosed_scale = 1.0 - assumed_share_total
        for probability, component, _location, _method in entries:
            item = by_species.setdefault(component["pokemonId"], dict(component))
            item["rawRate"] += probability * disclosed_scale
        for assumed_share, component, _location, _method in assumed_entries:
            item = by_species.setdefault(component["pokemonId"], dict(component))
            item["rawRate"] += raw_total * assumed_share
        components = list(by_species.values())
        for component in components:
            component["share"] = component["rawRate"] / raw_total
        components.sort(key=lambda item: (-item["share"], item["pokemon"]))

        incomplete = not (horde_3x or horde_5x) and raw_total < 0.94
        safari = is_safari(sample[2])
        notes: list[dict[str, str]] = []
        if assumed_entries:
            assumed_names = ", ".join(sorted({entry[1]["pokemon"] for entry in assumed_entries}))
            notes.append({
                "level": "assumption", "code": "temporary-unknown-rate",
                "message": f"Temporary planner assumption: {assumed_names} occupies {assumed_share_total:.0%} of this conditional horde table.",
            })
        if incomplete:
            notes.append({
                "level": "warning", "code": "incomplete-table",
                "message": f"Numeric table totals {raw_total:.2%}; rotating/special slots are not fully represented.",
            })
        if safari:
            notes.append({
                "level": "assumption", "code": "safari-catch",
                "message": "Safari result uses the global successful-catch assumption.",
            })
        if horde_3x or horde_5x:
            # Normal maps expose a 5% horde block. Early-game maps can instead
            # expose an exact 100% Sweet Scent-only table because regular walking
            # encounters cannot roll a horde there. Both representations are valid.
            # Near-100% totals such as 99.99% remain warnings as rounding/data loss.
            valid_horde_block = abs(raw_total - 0.05) <= 0.001
            valid_direct_sweet_scent = abs(raw_total - 1.0) <= 1e-9
            if not valid_horde_block and not valid_direct_sweet_scent:
                notes.append({
                    "level": "warning", "code": "horde-block",
                    "message": f"Direct Sweet Scent table totals {raw_total:.2%}; expected an exact 100% (or a normal 5% horde block).",
                })

        location_by_species: dict[int, dict[str, Any]] = {}
        for _probability, component, component_location, _method in entries:
            location_by_species[int(component["pokemonId"])] = component_location
        for _share, component, component_location, _method in assumed_entries:
            location_by_species[int(component["pokemonId"])] = component_location
        location_hazards = merge_hazards([
            hazard
            for component in components
            for hazard in hazards_for(
                monster_by_id[int(component["pokemonId"])],
                location_by_species.get(int(component["pokemonId"]), sample[2]),
                method,
            )
        ])
        all_component_locations = list(location_by_species.values()) or [sample[2]]
        location_level_min = min(int(item.get("min_level") or 1) for item in all_component_locations)
        location_level_max = max(int(item.get("max_level") or item.get("min_level") or 1) for item in all_component_locations)

        base = {
            "week": WEEK_BY_SEASON.get(str(season), str(season)),
            "season": season,
            "times": [time_name],
            "timeLabel": time_name,
            "method": method,
            "safari": safari,
            "lure": False,
            "incomplete": incomplete,
            "rawTotal": raw_total,
            "warning": f"Numeric table totals {raw_total:.2%}; rotating/special slots are not fully represented." if incomplete else "",
            "confidence": "low" if incomplete else "high",
            "locations": [{
                "region": region, "location": location_name, "locationId": location_id,
                "encounterTypes": [encounter_type],
                "levelMin": location_level_min, "levelMax": location_level_max,
                "hazards": location_hazards,
            }],
            "regions": [region],
            "components": components,
            "validation": notes,
        }
        rows.append(base)

        lure_entries = lure.get((region, location_id, location_name, encounter_type, season, time_name), [])
        if method in {"Singles", "Safari Singles"} and lure_entries:
            combined: dict[int, dict[str, Any]] = {}
            for component in components:
                item = dict(component)
                item["share"] *= 0.95
                item["rawRate"] = None
                combined[item["pokemonId"]] = item
            unique_lure = {item[0]["pokemonId"]: dict(item[0]) for item in lure_entries}
            lure_share = 0.05 / len(unique_lure)
            for item in unique_lure.values():
                if item["pokemonId"] in combined:
                    combined[item["pokemonId"]]["share"] += lure_share
                else:
                    item["share"] = lure_share
                    item["rawRate"] = None
                    item["lureExclusive"] = True
                    combined[item["pokemonId"]] = item
            lure_components = list(combined.values())
            lure_components.sort(key=lambda item: (-item["share"], item["pokemon"]))
            lure_method = "Lure Safari Singles" if method == "Safari Singles" else "Lure Singles"
            lure_notes = list(notes) + [{
                "level": "assumption", "code": "lure-slot",
                "message": "Lure-exclusive species share a modeled 5% slot.",
            }]
            lure_row = copy.deepcopy(base)
            lure_location_hazards = list(location_hazards)
            lure_locations_by_species = {int(component["pokemonId"]): location for component, location in lure_entries}
            for component in unique_lure.values():
                monster = monster_by_id[int(component["pokemonId"])]
                component_location = lure_locations_by_species.get(int(component["pokemonId"]), sample[2])
                lure_location_hazards.extend(hazards_for(monster, component_location, lure_method))
            lure_row["locations"][0]["hazards"] = merge_hazards(lure_location_hazards)
            lure_row["locations"][0]["levelMin"] = min(
                [location_level_min] + [int(location.get("min_level") or 1) for _component, location in lure_entries]
            )
            lure_row["locations"][0]["levelMax"] = max(
                [location_level_max] + [int(location.get("max_level") or location.get("min_level") or 1) for _component, location in lure_entries]
            )
            lure_row.update({
                "method": lure_method, "lure": True,
                "components": lure_components, "validation": lure_notes,
            })
            rows.append(lure_row)
    return rows


def collapse_location_type_time(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        location = row["locations"][0]
        key = (
            row["week"], row["season"], row["method"], row["safari"], row["lure"],
            row["incomplete"], round(float(row["rawTotal"]), 12), row["warning"],
            row["confidence"], location["region"], location["location"],
            int(location["locationId"]), component_key(row["components"]),
        )
        grouped[key].append(row)

    collapsed: list[dict[str, Any]] = []
    for matching in grouped.values():
        row = copy.deepcopy(matching[0])
        times = sorted({time for item in matching for time in item["times"]}, key=TIME_ORDER.get)
        encounter_types = sorted({
            encounter_type
            for item in matching for location in item["locations"]
            for encounter_type in location["encounterTypes"]
        })
        row["times"] = times
        row["timeLabel"] = "Any time" if times == ["Morning", "Day", "Night"] else " & ".join(times)
        row["locations"][0]["encounterTypes"] = encounter_types
        for item in matching[1:]:
            merge_location_details(row["locations"][0], item["locations"][0])
        refresh_group_hazards(row)
        collapsed.append(row)
    return collapsed


def merge_alternative_locations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        key = (
            row["week"], row["season"], tuple(row["times"]), row["timeLabel"], row["method"],
            row["safari"], row["lure"], row["incomplete"], round(float(row["rawTotal"]), 12),
            row["warning"], row["confidence"], component_key(row["components"]),
            tuple((note["level"], note["code"], note["message"]) for note in row["validation"]),
        )
        grouped[key].append(row)

    merged: list[dict[str, Any]] = []
    for matching in grouped.values():
        row = copy.deepcopy(matching[0])
        locations: dict[tuple[Any, ...], dict[str, Any]] = {}
        for item in matching:
            for location in item["locations"]:
                key = (location["region"], location["location"], int(location["locationId"]))
                if key not in locations:
                    locations[key] = copy.deepcopy(location)
                else:
                    merge_location_details(locations[key], location)
        row["locations"] = sorted(locations.values(), key=lambda item: (item["region"], item["location"], item["locationId"]))
        row["regions"] = sorted({item["region"] for item in row["locations"]})
        refresh_group_hazards(row)
        merged.append(row)
    return merged


def build_special_groups(
    base_groups: list[dict[str, Any]], monsters: list[dict[str, Any]], pokemon_by_id: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    special: list[dict[str, Any]] = []
    for source in base_groups:
        if source["method"] == "5x Horde":
            row = copy.deepcopy(source)
            row["method"] = "5x Horde (Slowed)"
            row["validation"].append({
                "level": "assumption", "code": "slowed-horde-speed",
                "message": "Same Sweet Scent table, using the editable slower 5× horde encounters/hour assumption.",
            })
            special.append(row)
        elif source["method"] == "3x Horde":
            row = copy.deepcopy(source)
            row["method"] = "3x Horde (Slowed)"
            row["validation"].append({
                "level": "assumption", "code": "slowed-horde-speed",
                "message": "Same Sweet Scent table, using the editable slower 3× horde encounters/hour assumption.",
            })
            special.append(row)
        elif source["method"] == "Fishing":
            row = copy.deepcopy(source)
            row["method"] = "Fishing + Chum Bucket"
            row["confidence"] = "medium"
            row["validation"].append({
                "level": "assumption", "code": "chum-speed",
                "message": "Uses the same rod encounter table. Chum effects are represented through the editable encounters/hour value.",
            })
            special.append(row)
        elif source["method"] == "Lure Singles" and source.get("lure"):
            water_locations = [copy.deepcopy(item) for item in source["locations"] if "Water" in item.get("encounterTypes", [])]
            if water_locations:
                for method, code, message in (
                    ("Fishing + Lure", "fishing-lure", "Uses the Water lure table. Lure-exclusive species occupy the modeled 5% slot; fishing speed is editable."),
                    ("Fishing + Lure + Chum Bucket", "fishing-lure-chum", "Uses the Water lure table with the modeled 5% lure-exclusive slot. Chum is represented through the editable encounters/hour value."),
                ):
                    row = copy.deepcopy(source)
                    row["method"] = method
                    row["locations"] = water_locations
                    row["regions"] = sorted({item["region"] for item in water_locations})
                    row["confidence"] = "medium"
                    row["validation"].append({"level": "assumption", "code": code, "message": message})
                    special.append(row)

    honey_rows: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for monster in monsters:
        pokemon = pokemon_by_id.get(int(monster["id"]))
        if pokemon is None:
            continue
        for original in monster.get("locations", []):
            location = dict(original)
            location["type"] = canonical_type(location.get("type"))
            if location["type"] == "Honey Tree":
                honey_rows.append((monster, pokemon, location))

    for season, week in WEEK_BY_SEASON.items():
        for time_name, field in TIME_FIELDS:
            by_species: dict[int, dict[str, Any]] = {}
            honey_hazards: list[dict[str, Any]] = []
            honey_levels: list[tuple[int, int]] = []
            raw_total = 0.0
            for monster, pokemon, location in honey_rows:
                probability = parse_percent(location.get(field))
                if probability is None:
                    continue
                raw_total += probability
                honey_hazards.extend(hazards_for(monster, location, "Honey Tree"))
                honey_levels.append((
                    int(location.get("min_level") or 1),
                    int(location.get("max_level") or location.get("min_level") or 1),
                ))
                item = by_species.setdefault(int(monster["id"]), {
                    "pokemonId": int(monster["id"]), "pokemon": monster["name"], "share": 0.0,
                    "tier": int(pokemon["tier"]), "points": int(pokemon["points"]), "line": pokemon["line"],
                    "lureExclusive": False, "rawRate": 0.0,
                })
                item["share"] += probability
                item["rawRate"] += probability
            if raw_total <= 0:
                continue
            components = list(by_species.values())
            for component in components:
                component["share"] /= raw_total
            components.sort(key=lambda item: (-item["share"], item["pokemon"]))
            special.append({
                "week": week, "season": season, "times": [time_name], "timeLabel": time_name,
                "method": "Honey Tree", "safari": False, "lure": False,
                "incomplete": raw_total < 0.94, "rawTotal": raw_total,
                "warning": "" if raw_total >= 0.94 else f"Numeric table totals {raw_total:.2%}.",
                "confidence": "medium",
                "locations": [{
                    "region": "Sinnoh", "location": "Honey Tree", "locationId": -1,
                    "encounterTypes": ["Honey Tree"],
                    "levelMin": min((value[0] for value in honey_levels), default=1),
                    "levelMax": max((value[1] for value in honey_levels), default=1),
                    "hazards": merge_hazards([
                        hazard for hazard in honey_hazards if int(hazard["pokemonId"]) in by_species
                    ]),
                }],
                "regions": ["Sinnoh"], "components": components,
                "validation": [{
                    "level": "assumption", "code": "honey-tree-speed",
                    "message": "Encounter composition is from the Dex. Encounters/hour is an editable active tree-checking assumption and excludes waiting time.",
                }],
            })

    for season, week in WEEK_BY_SEASON.items():
        for pokemon_id, region, location_name in FOSSILS:
            pokemon = pokemon_by_id[pokemon_id]
            special.append({
                "week": week, "season": season, "times": ["Morning", "Day", "Night"], "timeLabel": "Any time",
                "method": "Fossil", "safari": False, "lure": False, "incomplete": False,
                "rawTotal": 1.0, "warning": "", "confidence": "medium",
                "locations": [{
                    "region": region, "location": location_name, "locationId": -1000 - pokemon_id,
                    "encounterTypes": ["Fossil revival"],
                    "levelMin": 1, "levelMax": 1, "hazards": [],
                }],
                "regions": [region],
                "components": [{
                    "pokemonId": pokemon_id, "pokemon": pokemon["name"], "share": 1.0,
                    "tier": int(pokemon["tier"]), "points": int(pokemon["points"]), "line": pokemon["line"],
                    "lureExclusive": False, "rawRate": 1.0,
                }],
                "validation": [{
                    "level": "assumption", "code": "fossil-speed",
                    "message": "Fossil revival is a guaranteed-species hunt. Encounters/hour is editable, and the event wild-only shiny boost is not applied.",
                }],
            })
    return special


def build_validation(
    groups: list[dict[str, Any]], base_groups: list[dict[str, Any]], raw_count: int, collapsed_count: int
) -> dict[str, Any]:
    all_notes = [note for group in groups for note in group.get("validation", [])]
    summary = {
        "rawVariants": raw_count + (len(groups) - len(base_groups)),
        "locationTimeCollapsed": collapsed_count,
        "displayGroups": len(groups),
        "mergedGroups": sum(len(group.get("locations", [])) > 1 for group in groups),
        "anyTimeGroups": sum(group.get("timeLabel") == "Any time" for group in groups),
        "highConfidence": sum(group.get("confidence") == "high" for group in groups),
        "mediumConfidence": sum(group.get("confidence") == "medium" for group in groups),
        "lowConfidence": sum(group.get("confidence") == "low" for group in groups),
        "groupsWithNotes": sum(bool(group.get("validation")) for group in groups),
        "fatalChecks": sum(note.get("level") == "fatal" for note in all_notes),
        "warnings": sum(note.get("level") == "warning" for note in all_notes),
        "assumptions": sum(note.get("level") == "assumption" for note in all_notes),
        "hazardGroups": sum(bool(group.get("hazards")) for group in groups),
        "criticalHazardGroups": sum(group.get("hazardSeverity") == "critical" for group in groups),
        "hazardLocations": sum(bool(location.get("hazards")) for group in groups for location in group.get("locations", [])),
        "hazardSpecies": len({
            int(hazard["pokemonId"]) for group in groups for hazard in group.get("hazards", [])
        }),
    }
    issues = []
    for group in base_groups:
        if group.get("validation"):
            issues.append({
                "groupId": group["id"], "method": group["method"],
                "locations": [f"{item['region']} · {item['location']}" for item in group["locations"]],
                "notes": group["validation"],
            })
    method_messages = {
        "5x Horde (Slowed)": "Same exact 5× Sweet Scent encounter tables; only encounters/hour differs.",
        "3x Horde (Slowed)": "Same exact 3× Sweet Scent encounter tables; only encounters/hour differs.",
        "Fishing + Chum Bucket": "Rod table is unchanged; Chum is modeled through encounters/hour.",
        "Fishing + Lure": "Uses Water lure compositions with the modeled lure-exclusive slot.",
        "Fishing + Lure + Chum Bucket": "Uses Water lure compositions; Chum is modeled through encounters/hour.",
        "Honey Tree": "Dex composition is exact; active encounters/hour excludes the tree waiting period.",
        "Fossil": "Guaranteed species; speed is editable and wild-only event boost is excluded.",
    }
    for method, message in method_messages.items():
        example = next((group for group in groups if group["method"] == method), None)
        issues.append({
            "groupId": example["id"] if example else 0, "method": method,
            "locations": [f"{item['region']} · {item['location']}" for item in (example["locations"] if example else [])],
            "notes": [{
                "level": "assumption", "code": re.sub(r"[^a-z0-9]+", "-", method.lower()).strip("-"),
                "message": message,
            }],
        })
    return {"summary": summary, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dump_zip", type=Path)
    args = parser.parse_args()

    pokemon = load_assignment(POKEMON_PATH, "WAR_POKEMON")
    pokemon_by_id = {int(item["id"]): item for item in pokemon}
    monsters, dump_hash = load_dump(args.dump_zip)

    raw_groups = build_raw_groups(monsters, pokemon_by_id)
    collapsed = collapse_location_type_time(raw_groups)
    base_groups = merge_alternative_locations(collapsed)
    special_groups = build_special_groups(base_groups, monsters, pokemon_by_id)
    groups = base_groups + special_groups
    for group in groups:
        refresh_group_hazards(group)
    groups.sort(key=lambda group: (
        group["week"], group["season"], group["method"],
        group["regions"][0] if group.get("regions") else "",
        group["locations"][0]["location"] if group.get("locations") else "",
        group["timeLabel"],
        component_key(group["components"]),
    ))
    for index, group in enumerate(groups, start=1):
        group["id"] = index

    # Re-select base rows after IDs have been assigned, so issue links are valid.
    base_methods = {
        "3x Horde", "5x Horde", "Lure Singles", "Singles", "Fishing",
        "Safari Singles", "Headbutt", "Rock Smash", "Lure Safari Singles",
    }
    base_with_ids = [group for group in groups if group["method"] in base_methods]
    validation = build_validation(groups, base_with_ids, len(raw_groups), len(collapsed))

    GROUPS_PATH.write_text(
        "window.WAR_GROUPS=" + json.dumps(groups, ensure_ascii=False, separators=(",", ":")) + ";\n" +
        "window.WAR_VALIDATION=" + json.dumps(validation, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    incomplete_raw = sum(bool(group["incomplete"]) for group in raw_groups)
    meta = {
        "monsters_in_dump": len(monsters),
        "tiered_species_ids": len(pokemon),
        "ranking_variants": validation["summary"]["rawVariants"],
        "complete_variants": len(raw_groups) - incomplete_raw,
        "incomplete_variants": incomplete_raw,
        "methodology": {
            "hordes": "Normal 5% horde blocks and exact 100% early-route Sweet Scent-only tables are both normalized conditionally; near-100% rounding totals remain warnings.",
            "lures": "A 5% total lure-exclusive slot is split equally when a location has multiple lure-exclusive species.",
            "special_tables": "Numeric encounter groups below 94% total are flagged incomplete and sorted after complete groups.",
            "safari": "Safari Zone Gate is treated as a normal map; actual Safari Zones and the Great Marsh use the global successful-catch assumption.",
            "not_ranked": "Alpha schedules, legendary/mythical encounters, other unknown-rate phenomena/special encounters, eggs and Game Corner are not ranked.",
            "zorua_assumption": "Until a confirmed rate is exposed, Lostlorn Forest Zorua is modeled as 5% of the conditional 3× horde pool and the disclosed species share the remaining 95%.",
            "chum": "Chum keeps the fishing species table; additional encounters are represented through editable method speed.",
            "fossil": "Fossil groups are guaranteed-species revivals and do not receive the event wild-only shiny boost.",
            "dump_cleanup": "Decorated region labels, a prefixed Super Rod label, and literal control characters in unrelated strings are canonicalized while importing.",
            "safety_warnings": "Possible wild last-four level-up moves are reconstructed across each encounter level range. Self-KO, recoil, HP-cost, confusion and conditional sunlight-damage risks are flagged; Perish Song is excluded for hordes.",
        },
        "siteVersion": "0.8.3",
        "generatedAt": "2026-07-31",
        "encounterSource": "PokeMMO moddable resources dump uploaded 2026-07-30",
        "encounterDumpSha256": dump_hash,
        "spriteSource": "PokeMMO moddable resources sprite dump uploaded 2026-07-29",
        "storageKey": "pokemmo-wartool-state-v7",
    }
    META_PATH.write_text(
        "window.WAR_META=" + json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    methods = collections.Counter(group["method"] for group in groups)
    print(f"Loaded monsters: {len(monsters)}")
    print(f"Raw ranking rows: {len(raw_groups):,}")
    print(f"Location/time groups: {len(collapsed):,}")
    print(f"Display groups: {len(groups):,}")
    for method, count in sorted(methods.items()):
        print(f"  {method}: {count:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
