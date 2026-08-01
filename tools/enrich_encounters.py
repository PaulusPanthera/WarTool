from __future__ import annotations

import collections
import copy
from typing import Any

JOHTO_SAFARI_AREAS = {
    343: "Plains", 344: "Meadow", 345: "Savannah", 346: "Peak",
    347: "Rocky Beach", 348: "Wetland", 349: "Forest", 350: "Swamp",
    351: "Marshland", 352: "Wasteland", 353: "Mountain", 354: "Desert",
}
HOENN_SAFARI_AREAS = {844: 1, 588: 2, 76: 3, 332: 4, 3404: 5, 3148: 6}
START_DELAY_ABILITIES = {
    "Intimidate", "Reactive Gas", "Pressure", "Unnerve", "Download",
    "Frisk", "Forewarn", "Anticipation", "Trace", "Mold Breaker",
    "Turboblaze", "Teravolt", "Drought", "Drizzle", "Sand Stream",
    "Snow Warning", "Air Lock", "Cloud Nine", "Slow Start", "Imposter",
}
HAZARD_MOVES = {
    "Selfdestruct": ("self-ko", "critical", "The user faints immediately.", "Use Damp; against Koffing/Weezing prefer Imprison because Reactive Gas can suppress Damp."),
    "Explosion": ("self-ko", "critical", "The user faints immediately.", "Use Damp; against Koffing/Weezing prefer Imprison because Reactive Gas can suppress Damp."),
    "Memento": ("self-ko", "critical", "The user faints immediately.", "Taunt, Imprison or an appropriate trapping/control setup prevents it."),
    "Final Gambit": ("self-ko", "critical", "The user faints immediately.", "Use a Ghost-type, Taunt or Imprison."),
    "Healing Wish": ("self-ko", "critical", "The user faints immediately.", "Taunt or Imprison prevents it."),
    "Lunar Dance": ("self-ko", "critical", "The user faints immediately.", "Taunt or Imprison prevents it."),
    "Perish Song": ("countdown", "critical", "The user can faint when the perish count reaches zero.", "Catch or reset the battle before the count expires."),
    "Take Down": ("recoil", "warning", "The user takes recoil damage.", "Use a Ghost-type or reduce turns spent battling."),
    "Double-Edge": ("recoil", "warning", "The user takes recoil damage.", "Use a Ghost-type or reduce turns spent battling."),
    "Submission": ("recoil", "warning", "The user takes recoil damage.", "Use a Ghost-type or reduce turns spent battling."),
    "Brave Bird": ("recoil", "warning", "The user takes recoil damage.", "Use a resistant target and avoid extended battles."),
    "Flare Blitz": ("recoil", "warning", "The user takes recoil damage.", "Use a resistant target and avoid extended battles."),
    "Head Smash": ("recoil", "warning", "The user takes heavy recoil damage.", "Use a Ghost-type or a highly resistant target."),
    "Volt Tackle": ("recoil", "warning", "The user takes recoil damage.", "Use a Ground-type."),
    "Wood Hammer": ("recoil", "warning", "The user takes recoil damage.", "Use a resistant target and avoid extended battles."),
    "Wild Charge": ("recoil", "warning", "The user takes recoil damage.", "Use a Ground-type."),
    "Head Charge": ("recoil", "warning", "The user takes recoil damage.", "Use a Ghost-type."),
    "Jump Kick": ("crash", "warning", "The user takes crash damage if the move misses or fails.", "Avoid Ghost-types and Protect-like failure conditions."),
    "Hi Jump Kick": ("crash", "warning", "The user takes crash damage if the move misses or fails.", "Avoid Ghost-types and Protect-like failure conditions."),
    "Curse": ("hp-loss", "warning", "Ghost-type users sacrifice half of their maximum HP.", "Taunt or Imprison prevents it."),
    "Thrash": ("confusion", "warning", "The user becomes confused after the locked attack ends.", "Catch quickly or use Own Tempo support."),
    "Outrage": ("confusion", "warning", "The user becomes confused after the locked attack ends.", "Catch quickly or use Own Tempo support."),
    "Petal Dance": ("confusion", "warning", "The user becomes confused after the locked attack ends.", "Catch quickly or use Own Tempo support."),
    "Belly Drum": ("hp-loss", "warning", "The user loses half of its maximum HP when the move succeeds.", "Taunt or Imprison prevents it."),
}
REDIRECTION_MOVES = {
    "Rage Powder": ("redirection", "critical", "In a horde it can redirect a targeted attack onto itself, potentially hitting the shiny.", "Do not use targeted cleanup attacks until the redirect user is controlled; Taunt or spread-safe play helps."),
    "Follow Me": ("redirection", "critical", "In a horde it can redirect a targeted attack onto itself, potentially hitting the shiny.", "Do not use targeted cleanup attacks until the redirect user is controlled; Taunt or spread-safe play helps."),
}
HAZARD_ABILITIES = {
    "Dry Skin": ("weather", "warning", "The Pokémon loses HP each turn in harsh sunlight.", "Avoid harsh sunlight."),
    "Solar Power": ("weather", "warning", "The Pokémon loses HP each turn in harsh sunlight.", "Avoid harsh sunlight."),
}


def normalize_safari_location(region: str, location_id: int, location: str) -> str:
    if region == "Johto" and location_id in JOHTO_SAFARI_AREAS:
        return f"Safari Zone — {JOHTO_SAFARI_AREAS[location_id]}"
    if region == "Hoenn" and location_id in HOENN_SAFARI_AREAS:
        label = location.replace("Safari Zone", "").strip(" -—()")
        return f"Safari Zone — {label} (Area {HOENN_SAFARI_AREAS[location_id]})"
    if region == "Kanto" and location.startswith("Safari Zone ("):
        return location.replace("Safari Zone (", "Safari Zone — ").rstrip(")")
    if region == "Sinnoh" and location.startswith("Great Marsh ("):
        return location.replace("Great Marsh (", "Great Marsh — ").rstrip(")")
    return location


def normalize_safari_type(region: str, encounter_type: str, safari: bool) -> str:
    if safari and region == "Johto" and encounter_type == "Cave":
        return "Grass"
    if safari and region == "Sinnoh" and encounter_type == "Inside":
        return "Grass"
    return encounter_type


def wild_moves_at_level(level_moves: list[dict[str, Any]], level: int) -> list[str]:
    known: list[str] = []
    for move in level_moves:
        try:
            learned = int(move.get("level", 0) or 0)
        except (TypeError, ValueError):
            continue
        if learned > level:
            continue
        name = str(move.get("name") or "").strip()
        if not name:
            continue
        if name in known:
            known.remove(name)
        known.append(name)
    return known[-4:]


def compact_ranges(levels: set[int]) -> str:
    if not levels:
        return ""
    ordered = sorted(levels)
    out: list[str] = []
    start = prev = ordered[0]
    for level in ordered[1:]:
        if level == prev + 1:
            prev = level
            continue
        out.append(str(start) if start == prev else f"{start}–{prev}")
        start = prev = level
    out.append(str(start) if start == prev else f"{start}–{prev}")
    return ", ".join(out)


def safety_maps(monsters: list[dict[str, Any]]) -> tuple[dict[int, list[dict[str, Any]]], dict[int, list[str]], dict[int, list[str]]]:
    moves: dict[int, list[dict[str, Any]]] = {}
    slow: dict[int, list[str]] = {}
    abilities: dict[int, list[str]] = {}
    for mon in monsters:
        pid = int(mon["id"])
        moves[pid] = [m for m in mon.get("moves", []) if str(m.get("type", "")).lower() == "level"]
        normal_abilities: list[str] = []
        for ability in mon.get("abilities", [])[:2]:
            name = str(ability.get("name") or "").strip()
            if name and name != "-" and name not in normal_abilities:
                normal_abilities.append(name)
        abilities[pid] = normal_abilities
        slow[pid] = [name for name in normal_abilities if name in START_DELAY_ABILITIES]
    return moves, slow, abilities


def hazard_rows(pid: int, pokemon: str, level_min: int, level_max: int, method: str, safari: bool,
                level_moves: dict[int, list[dict[str, Any]]], abilities: dict[int, list[str]]) -> list[dict[str, Any]]:
    if safari or pid <= 0:
        return []
    by_name: dict[str, set[int]] = collections.defaultdict(set)
    for level in range(max(1, level_min), max(level_min, level_max) + 1):
        for move in wild_moves_at_level(level_moves.get(pid, []), level):
            rules = HAZARD_MOVES
            if "Horde" in method and move in REDIRECTION_MOVES:
                rules = REDIRECTION_MOVES
            if move == "Perish Song" and "Horde" in method:
                continue
            if move in rules:
                by_name[move].add(level)
    rows: list[dict[str, Any]] = []
    for name, levels in by_name.items():
        kind, severity, consequence, counter = (REDIRECTION_MOVES if name in REDIRECTION_MOVES else HAZARD_MOVES)[name]
        rows.append({"pokemonId": pid, "pokemon": pokemon, "name": name, "kind": kind, "severity": severity,
                     "levelRange": compact_ranges(levels), "consequence": consequence, "counter": counter})
    for ability in abilities.get(pid, []):
        if ability in HAZARD_ABILITIES:
            kind, severity, consequence, counter = HAZARD_ABILITIES[ability]
            rows.append({"pokemonId": pid, "pokemon": pokemon, "name": ability, "kind": kind, "severity": severity,
                         "levelRange": f"{level_min}–{level_max}", "consequence": consequence, "counter": counter})
    return rows


def _base_key(row: dict[str, Any]) -> tuple[Any, ...]:
    loc = row["locations"][0]
    return (row["week"], row["season"], tuple(row["times"]), loc["region"], int(loc["locationId"]),
            loc["location"], tuple(loc["encounterTypes"]))


def _component_from_source(component: dict[str, Any], event_rate: float, count: int, label: str) -> dict[str, Any]:
    out = copy.deepcopy(component)
    out["sources"] = [{"eventRate": event_rate, "count": count, "label": label}]
    out["shownWeight"] = event_rate * count
    return out


def _combine_components(rows: list[tuple[dict[str, Any], int, str]], unknown_event: float = 0.0) -> tuple[list[dict[str, Any]], float]:
    combined: dict[int, dict[str, Any]] = {}
    for row, count, label in rows:
        for component in row["components"]:
            event_rate = float(component.get("rawRate") or 0)
            pid = int(component["pokemonId"])
            item = combined.get(pid)
            source = {"eventRate": event_rate, "count": count, "label": label}
            if item is None:
                item = copy.deepcopy(component)
                item["sources"] = [source]
                item["shownWeight"] = event_rate * count
                combined[pid] = item
            else:
                item["shownWeight"] += event_rate * count
                item.setdefault("sources", []).append(source)
                item["minLevel"] = min(int(item.get("minLevel", 0)), int(component.get("minLevel", 0)))
                item["maxLevel"] = max(int(item.get("maxLevel", 0)), int(component.get("maxLevel", 0)))
    if unknown_event > 0:
        combined[0] = {"pokemonId": 0, "pokemon": "Unknown rotational", "tier": -1, "points": 0,
                       "line": "__unknown__", "lureExclusive": False, "unknown": True,
                       "rawRate": unknown_event, "shownWeight": unknown_event,
                       "minLevel": 0, "maxLevel": 0,
                       "sources": [{"eventRate": unknown_event, "count": 1, "label": "Undocumented rotational slot"}]}
    shown_total = sum(float(item["shownWeight"]) for item in combined.values())
    components = list(combined.values())
    for item in components:
        item["share"] = float(item["shownWeight"]) / shown_total if shown_total else 0
    components.sort(key=lambda item: (-float(item["share"]), item["pokemon"]))
    return components, shown_total


def transform_random_tables(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hordes: dict[tuple[Any, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    normals: list[dict[str, Any]] = []
    lure_rows: dict[tuple[Any, ...], dict[str, Any]] = {}
    keep: list[dict[str, Any]] = []
    for row in rows:
        if row["method"] in {"3x Horde", "5x Horde"} and float(row["rawTotal"]) <= 0.11:
            hordes[_base_key(row)].append(row)
        elif row["method"] in {"Singles", "Safari Singles"} and not row.get("lure"):
            normals.append(row)
        elif row["method"] in {"Lure Singles", "Lure Safari Singles"}:
            lure_rows[_base_key(row)] = row
        else:
            keep.append(row)
    keep.extend(row for rows_ in hordes.values() for row in rows_)

    for normal in normals:
        key = _base_key(normal)
        matching = hordes.get(key, [])
        sources: list[tuple[dict[str, Any], int, str]] = [(normal, 1, "Single encounter")]
        for horde in matching:
            count = 5 if horde["method"].startswith("5x") else 3
            sources.append((horde, count, f"Natural {count}× horde"))
        event_total = float(normal["rawTotal"]) + sum(float(h["rawTotal"]) for h in matching)
        loc = normal["locations"][0]
        safari = bool(normal.get("safari"))
        unknown_event = 0.0
        safari_pool = None
        if safari and loc["region"] == "Johto" and "Grass" in loc["encounterTypes"] and event_total < 0.999:
            unknown_event = max(0.0, 1.0 - event_total)
            safari_pool = {"documentedTotal": event_total, "unknownShare": unknown_event, "label": "Base grass pool",
                           "note": "The dump documents 90%; block/rotation encounters occupy the remaining 10%."}
        elif safari and loc["region"] == "Sinnoh" and "Grass" in loc["encounterTypes"] and event_total < 0.999:
            unknown_event = max(0.0, 1.0 - event_total)
            safari_pool = {"documentedTotal": event_total, "unknownShare": unknown_event, "label": "Base grass pool",
                           "note": "The dump documents 80%; daily rotations occupy the remaining 20%."}
        components, shown_total = _combine_components(sources, unknown_event)
        row = copy.deepcopy(normal)
        row["components"] = components
        row["rawTotal"] = event_total
        row["shownTotal"] = shown_total
        row["containsNaturalHordes"] = bool(matching)
        if matching:
            row["validation"] = [n for n in row.get("validation", []) if n.get("code") != "incomplete-table"]
            row["validation"].append({"level": "assumption", "code": "natural-horde-roll",
                                      "message": "Ordinary encounters include the natural horde roll; shares are weighted by individual Pokémon shown."})
            row["incomplete"] = False
            row["warning"] = ""
            row["confidence"] = "high" if abs(event_total - 1.0) <= 0.03 else "medium"
        if safari_pool:
            row["safariPool"] = safari_pool
            row["incomplete"] = False
            row["warning"] = ""
            row["confidence"] = "medium"
            row["validation"] = [n for n in row.get("validation", []) if n.get("code") != "incomplete-table"]
            row["validation"].append({"level": "assumption", "code": "safari-rotational-coverage",
                                      "message": safari_pool["note"] + " Unknown rotationals contribute 0 points, so this is a conservative lower bound."})
        keep.append(row)

        lure_old = lure_rows.get(key)
        if lure_old:
            lure_ids = [c for c in lure_old["components"] if c.get("lureExclusive")]
            scaled: dict[int, dict[str, Any]] = {}
            for component in components:
                item = copy.deepcopy(component)
                item["shownWeight"] = float(component.get("shownWeight", component["share"])) * 0.95
                item["share"] = 0
                item["sources"] = [dict(src, eventRate=float(src["eventRate"]) * 0.95) for src in component.get("sources", [])]
                scaled[int(item["pokemonId"])] = item
            if lure_ids:
                each = 0.05 / len(lure_ids)
                for component in lure_ids:
                    item = copy.deepcopy(component)
                    item["rawRate"] = each
                    item["shownWeight"] = each
                    item["sources"] = [{"eventRate": each, "count": 1, "label": "Lure-exclusive encounter"}]
                    scaled[int(item["pokemonId"])] = item
            total = sum(float(c["shownWeight"]) for c in scaled.values())
            lure_components = list(scaled.values())
            for c in lure_components:
                c["share"] = float(c["shownWeight"]) / total if total else 0
            lure_components.sort(key=lambda c: (-float(c["share"]), c["pokemon"]))
            lure = copy.deepcopy(row)
            lure["method"] = "Lure Safari Singles" if safari else "Lure Singles"
            lure["lure"] = True
            lure["components"] = lure_components
            lure["rawTotal"] = 1.0
            lure["shownTotal"] = total
            lure["validation"] = list(row.get("validation", [])) + [{"level": "assumption", "code": "lure-slot",
                "message": "Lure uses 95% of the complete random encounter pool plus a 5% lure-exclusive roll."}]
            if safari_pool:
                lure["safariPool"] = dict(safari_pool, unknownShare=unknown_event * 0.95,
                    note=safari_pool["note"] + f" With Lure, the unknown rotational share is {unknown_event * 0.95:.1%} and the lure slot is 5%.")
            keep.append(lure)
    return keep


def add_safety(rows: list[dict[str, Any]], monsters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    moves, slow, abilities = safety_maps(monsters)
    for row in rows:
        safari = bool(row.get("safari"))
        group_hazards: list[dict[str, Any]] = []
        group_slow: list[dict[str, Any]] = []
        for component in row.get("components", []):
            pid = int(component.get("pokemonId", 0))
            if pid <= 0:
                component["hazards"] = []
                component["slowAbilities"] = []
                continue
            level_min = int(component.get("minLevel", 1) or 1)
            level_max = int(component.get("maxLevel", level_min) or level_min)
            component["hazards"] = hazard_rows(pid, component["pokemon"], level_min, level_max, row["method"], safari, moves, abilities)
            component["slowAbilities"] = slow.get(pid, [])
            group_hazards.extend(copy.deepcopy(component["hazards"]))
            if component["slowAbilities"]:
                group_slow.append({"pokemonId": pid, "pokemon": component["pokemon"], "abilities": component["slowAbilities"]})
        row["hazards"] = group_hazards
        row["slowdowns"] = group_slow
    return rows
