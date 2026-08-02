from __future__ import annotations

import collections
import copy
import json
from pathlib import Path
from typing import Any

JOHTO_SAFARI_AREAS = {
    343: "Plains", 344: "Meadow", 345: "Savannah", 346: "Peak",
    347: "Rocky Beach", 348: "Wetland", 349: "Forest", 350: "Swamp",
    351: "Marshland", 352: "Wasteland", 353: "Mountain", 354: "Desert",
}
HOENN_SAFARI_AREAS = {844: 1, 588: 2, 76: 3, 332: 4, 3404: 5, 3148: 6}
SAFETY_RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "safety-rules.json"


def load_safety_rules(path: Path = SAFETY_RULES_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != 1:
        raise ValueError(f"Unsupported safety-rules schema in {path}")
    required = ("moveRules", "abilityRules", "heldItemRules", "speciesRules", "compoundRules", "startDelayAbilities")
    if any(key not in payload for key in required):
        raise ValueError(f"Incomplete safety-rules file: {path}")
    return payload


SAFETY_RULES = load_safety_rules()
START_DELAY_ABILITIES = set(SAFETY_RULES["startDelayAbilities"])
MOVE_RULES = SAFETY_RULES["moveRules"]
ABILITY_RULES = SAFETY_RULES["abilityRules"]
HELD_ITEM_RULES = SAFETY_RULES["heldItemRules"]
SPECIES_RULES = SAFETY_RULES["speciesRules"]
COMPOUND_RULES = SAFETY_RULES["compoundRules"]


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


def safety_maps(monsters: list[dict[str, Any]]) -> tuple[
    dict[int, list[dict[str, Any]]], dict[int, list[str]], dict[int, list[str]],
    dict[int, list[str]], dict[int, list[str]], dict[int, list[str]],
]:
    moves: dict[int, list[dict[str, Any]]] = {}
    slow: dict[int, list[str]] = {}
    normal_abilities: dict[int, list[str]] = {}
    all_abilities: dict[int, list[str]] = {}
    types: dict[int, list[str]] = {}
    held_items: dict[int, list[str]] = {}
    for mon in monsters:
        pid = int(mon["id"])
        moves[pid] = [m for m in mon.get("moves", []) if str(m.get("type", "")).lower() == "level"]
        normal: list[str] = []
        all_names: list[str] = []
        for index, ability in enumerate(mon.get("abilities", [])):
            name = str(ability.get("name") or "").strip(" -")
            if not name or name == "-":
                continue
            if name not in all_names:
                all_names.append(name)
            if index < 2 and name not in normal:
                normal.append(name)
        normal_abilities[pid] = normal
        all_abilities[pid] = all_names
        slow[pid] = [name for name in normal if name in START_DELAY_ABILITIES]
        types[pid] = [str(value or "").upper() for value in mon.get("types", []) if value]
        held_items[pid] = [str(item.get("name") or "") for item in mon.get("held_items", []) if item.get("name")]
    return moves, slow, normal_abilities, all_abilities, types, held_items


def component_contexts(method: str, encounter_types: list[str], sources: list[dict[str, Any]]) -> set[str]:
    contexts: set[str] = {"non-safari"}
    if "Horde" in method:
        contexts.add("explicit-horde")
        return contexts
    source_labels = [str(source.get("label") or "") for source in sources]
    has_single = any(label in {"Single encounter", "Lure-exclusive encounter"} for label in source_labels)
    has_natural = any(label.startswith("Natural ") and "horde" in label.lower() for label in source_labels)
    if has_single or not source_labels:
        contexts.add("singles")
    if has_natural:
        contexts.add("natural-horde")
    if "Lure" in method:
        contexts.update({"singles", "lure-double"})
    if "Dark Grass" in encounter_types:
        contexts.update({"singles", "dark-grass"})
    return contexts


def rule_applies(rule: dict[str, Any], pid: int, pokemon_types: list[str], contexts: set[str]) -> bool:
    allowed = set(rule.get("contexts", []))
    if allowed and not (allowed & contexts):
        return False
    species = rule.get("speciesCondition")
    if species and pid not in {int(value) for value in species}:
        return False
    type_condition = rule.get("typeCondition") or {}
    required = str(type_condition.get("includes") or "").upper()
    if required and required not in pokemon_types:
        return False
    return True


def safety_row(pid: int, pokemon: str, name: str, rule: dict[str, Any], level_range: str,
               contexts: set[str], consequence: str | None = None, counter: str | None = None,
               details: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {
        "pokemonId": pid,
        "pokemon": pokemon,
        "name": name,
        "category": str(rule.get("category") or "setup-interaction"),
        "kind": str(rule.get("mechanic") or rule.get("category") or "warning"),
        "severity": str(rule.get("severity") or "warning"),
        "levelRange": level_range,
        "contexts": sorted(contexts),
        "consequence": consequence if consequence is not None else str(rule.get("effect") or ""),
        "counter": counter if counter is not None else str(rule.get("preparation") or ""),
        "verificationStatus": str(rule.get("verification") or "confirmed"),
    }
    if details:
        row["details"] = details
    return row


def redirection_text(move_name: str, pokemon: str, contexts: set[str], worry_seed_overlap: bool) -> tuple[str, str]:
    if "explicit-horde" in contexts:
        consequence = "In this horde it can redirect a targeted cleanup attack onto itself, potentially causing the shiny to be hit."
    elif "lure-double" in contexts:
        consequence = "Only dangerous when the Lure opens a wild double battle; it can redirect a targeted cleanup attack onto itself. It is harmless in a true single battle."
    elif "dark-grass" in contexts:
        consequence = "Dark Grass can open a wild double battle, where it can redirect a targeted cleanup attack onto itself. It is harmless in a true single battle."
    else:
        consequence = "This species can appear through the natural horde roll and redirect a targeted cleanup attack onto itself. It is harmless when encountered alone."
    priority = "A faster Extreme Speed or Feint user can act first at the same +2 priority; Taunt or Imprison are alternatives."
    if move_name == "Rage Powder":
        immunity = "Grass types and Overcoat ignore Rage Powder."
        if pokemon in {"Hoppip", "Skiploom"}:
            immunity += " Do not rely only on Overcoat against this species because Worry Seed can remove it."
        counter = f"{priority} {immunity}"
    else:
        counter = f"{priority} Grass typing and Overcoat do not ignore Follow Me."
    return consequence, counter


def hazard_rows(pid: int, pokemon: str, level_min: int, level_max: int, method: str, safari: bool,
                encounter_types: list[str], sources: list[dict[str, Any]],
                level_moves: dict[int, list[dict[str, Any]]], normal_abilities: dict[int, list[str]],
                all_abilities: dict[int, list[str]], pokemon_types: dict[int, list[str]],
                held_items: dict[int, list[str]]) -> list[dict[str, Any]]:
    if safari or pid <= 0:
        return []
    contexts = component_contexts(method, encounter_types, sources)
    types = pokemon_types.get(pid, [])
    active_by_level: dict[int, set[str]] = {}
    move_levels: dict[str, set[int]] = collections.defaultdict(set)
    for level in range(max(1, level_min), max(level_min, level_max) + 1):
        active = set(wild_moves_at_level(level_moves.get(pid, []), level))
        active_by_level[level] = active
        for move in active:
            rule = MOVE_RULES.get(move)
            if rule and rule_applies(rule, pid, types, contexts):
                move_levels[move].add(level)

    rows: list[dict[str, Any]] = []
    for name, levels in move_levels.items():
        rule = MOVE_RULES[name]
        consequence = None
        counter = None
        details = None
        if rule.get("category") == "redirection":
            worry_overlap = any("Worry Seed" in active for active in active_by_level.values())
            consequence, counter = redirection_text(name, pokemon, contexts, worry_overlap)
            details = {"worrySeedOverlap": worry_overlap}
        rows.append(safety_row(
            pid, pokemon, name, rule, compact_ranges(levels), contexts,
            consequence=consequence, counter=counter, details=details,
        ))

    for ability in normal_abilities.get(pid, []):
        rule = ABILITY_RULES.get(ability)
        if rule and rule_applies(rule, pid, types, contexts | {"weather"}):
            rows.append(safety_row(pid, pokemon, ability, rule, f"{level_min}–{level_max}", contexts | {"weather"}))

    for item_name, rule in HELD_ITEM_RULES.items():
        if any(item_name.lower() in held.lower() for held in held_items.get(pid, [])) and rule_applies(rule, pid, types, contexts):
            rows.append(safety_row(pid, pokemon, item_name, rule, f"{level_min}–{level_max}", contexts))

    species_rule = SPECIES_RULES.get(str(pid))
    if species_rule and rule_applies(species_rule, pid, types, contexts):
        # Avoid duplicating Ditto's move-level Transform preparation row; the species rule adds the Imposter context.
        rows = [row for row in rows if not (pid == 132 and row.get("name") == "Transform")]
        rows.append(safety_row(
            pid, pokemon, str(species_rule.get("name") or "Species preparation"), species_rule,
            f"{level_min}–{level_max}", contexts,
            details={"abilities": all_abilities.get(pid, [])},
        ))

    for compound in COMPOUND_RULES:
        species = {int(value) for value in compound.get("speciesCondition", [])}
        if pid not in species or not rule_applies(compound, pid, types, contexts):
            continue
        relevant = set(compound.get("activeMovesAny", []))
        minimum = int(compound.get("minimumActive", 2) or 2)
        active_names = sorted({move for active in active_by_level.values() for move in active if move in relevant})
        if len(active_names) < minimum:
            continue
        compound_levels = {level for level, active in active_by_level.items() if active & relevant}
        consequence = str(compound.get("effect") or "") + f" Active across this level range: {', '.join(active_names)}."
        counter = "Use Taunt or Imprison to cover the active risks together."
        if "Rage Powder" in active_names:
            counter += " A faster Extreme Speed or Feint can beat +2 redirection."
        if "Rage Powder" in active_names and "Worry Seed" in active_names:
            counter += " Do not rely only on Overcoat because another level in this encounter range can carry Worry Seed."
        rows.append(safety_row(
            pid, pokemon, str(compound.get("name") or "Compound setup"), compound,
            compact_ranges(compound_levels), contexts,
            consequence=consequence, counter=counter,
            details={"activeMoves": active_names},
        ))

    severity_order = {"critical": 0, "warning": 1, "preparation": 2}
    rows.sort(key=lambda row: (severity_order.get(row["severity"], 9), row["category"], row["name"]))
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
            safari_pool = {"key": "johto", "settingKey": "johtoSafariRotationalTier",
                           "documentedTotal": event_total, "unknownShare": unknown_event, "label": "Base grass pool",
                           "note": "The dump documents 90%; block/rotation encounters occupy the remaining 10%."}
        elif safari and loc["region"] == "Sinnoh" and "Grass" in loc["encounterTypes"] and event_total < 0.999:
            unknown_event = max(0.0, 1.0 - event_total)
            safari_pool = {"key": "greatMarsh", "settingKey": "greatMarshRotationalTier",
                           "documentedTotal": event_total, "unknownShare": unknown_event, "label": "Base grass pool",
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
                                      "message": safari_pool["note"] + " The rotational slot is unscored by default and can be assigned a tier in Settings."})
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
    moves, slow, normal_abilities, all_abilities, types, held_items = safety_maps(monsters)
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
            encounter_types = sorted({
                encounter_type
                for location in row.get("locations", [])
                for encounter_type in location.get("encounterTypes", [])
            })
            component["hazards"] = hazard_rows(
                pid, component["pokemon"], level_min, level_max, row["method"], safari,
                encounter_types, component.get("sources", []), moves, normal_abilities,
                all_abilities, types, held_items,
            )
            # Safari encounters do not enter the normal battle-intro sequence, so encounter-start abilities do not delay them.
            component["slowAbilities"] = [] if safari else slow.get(pid, [])
            group_hazards.extend(copy.deepcopy(component["hazards"]))
            if component["slowAbilities"]:
                group_slow.append({"pokemonId": pid, "pokemon": component["pokemon"], "abilities": component["slowAbilities"]})
        row["hazards"] = group_hazards
        row["slowdowns"] = group_slow
    return rows
