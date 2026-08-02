#!/usr/bin/env python3
"""Validate the static WARtool package before GitHub Pages deployment."""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_METHOD_SPEEDS = {
    "5x Horde": 1200,
    "5x Horde (Slowed)": 1000,
    "3x Horde": 720,
    "3x Horde (Slowed)": 600,
    "Lure Singles": 280,
    "Singles": 220,
    "Safari Singles": 300,
    "Lure Safari Singles": 300,
    "Fishing": 270,
    "Fishing + Lure": 340,
    "Fishing + Chum Bucket": 400,
    "Fishing + Lure + Chum Bucket": 500,
    "Rock Smash": 120,
    "Headbutt": 120,
    "Honey Tree": 60,
    "Fossil": 120,
}
TIER_POINTS = {0: 50, 1: 45, 2: 40, 3: 30, 4: 15, 5: 10, 6: 5, 7: 3}

EXPECTED_METHOD_COUNTS = {
    "5x Horde": 1887,
    "3x Horde": 621,
    "Lure Singles": 3435,
    "Singles": 4174,
    "Safari Singles": 400,
    "Lure Safari Singles": 75,
    "Fishing": 860,
    "Fishing + Lure": 1056,
    "Fishing + Chum Bucket": 860,
    "Fishing + Lure + Chum Bucket": 1056,
    "Rock Smash": 256,
    "Headbutt": 257,
    "Honey Tree": 12,
    "Fossil": 36,
}


class IdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.local_assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        for key in ("src", "href"):
            value = values.get(key)
            if not value or value.startswith(("http://", "https://", "#", "data:", "mailto:")):
                continue
            self.local_assets.append(value.split("?", 1)[0])


def load_assignment(path: Path, name: str) -> Any:
    text = path.read_text(encoding="utf-8")
    marker = f"window.{name}"
    start = text.find(marker)
    if start < 0:
        raise ValueError(f"{path.relative_to(ROOT)} does not define {marker}")
    start = text.find("=", start) + 1
    return json.JSONDecoder().raw_decode(text[start:].lstrip())[0]


def normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9♀♂]+", "", str(value or "").strip().lower().replace("’", "'"))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def score_demo_catches(catches: list[dict[str, Any]], pokemon_by_id: dict[int, dict[str, Any]]) -> tuple[int, int]:
    team_lines: set[str] = set()
    player_lines: dict[str, set[str]] = defaultdict(set)
    total = 0
    scored = 0
    for item in sorted(catches, key=lambda row: (row.get("caughtAt", ""), row.get("id", ""))):
        pokemon = pokemon_by_id[int(item["pokemonId"])]
        line = item.get("line") or pokemon["line"]
        duplicate = line in player_lines[item["playerId"]]
        if duplicate:
            base = 35 if item.get("alpha") else 1
        elif item.get("alpha"):
            base = 75
        elif item.get("egg"):
            base = max(35, int(pokemon["points"]))
        else:
            base = int(pokemon["points"])
        unique = 0 if line in team_lines else 8
        value = base + unique + (20 if item.get("secret") else 0) + (10 if item.get("safari") else 0)
        total += value
        scored += 1
        team_lines.add(line)
        player_lines[item["playerId"]].add(line)
    return total, scored


def main() -> int:
    errors: list[str] = []
    notes: list[str] = []

    required = [
        "index.html", "css/styles.css", "js/app.js", "data/groups.js", "data/pokemon.js",
        "data/meta.js", "data/roster.js", "data/live/state.json", "data/live/import-report.json",
        "data/live/sources.json", "favicon.svg", "site.webmanifest", ".nojekyll", "server.py",
        "START_WARTOOL.bat", "tools/rebuild_encounters.py", "tools/enrich_encounters.py",
        "tools/import_google_sheet.py", "tools/build_static_site.py", "tools/SETTINGS_SHEET_TEMPLATE.csv",
        "tools/GOOGLE_SHEET_SETUP.md", "tools/MUSH_WARtool_Google_Sheet_Template.xlsx",
        "assets/encounter-slowdown.png", "data/safari-rates.json", "data/safety-rules.json",
    ]
    for relative in required:
        if not (ROOT / relative).is_file():
            fail(errors, f"Missing required file: {relative}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    try:
        groups = load_assignment(ROOT / "data/groups.js", "WAR_GROUPS")
        validation = load_assignment(ROOT / "data/groups.js", "WAR_VALIDATION")
        pokemon = load_assignment(ROOT / "data/pokemon.js", "WAR_POKEMON")
        meta = load_assignment(ROOT / "data/meta.js", "WAR_META")
        roster = load_assignment(ROOT / "data/roster.js", "WAR_ROSTER")
        live = json.loads((ROOT / "data/live/state.json").read_text(encoding="utf-8"))
        import_report = json.loads((ROOT / "data/live/import-report.json").read_text(encoding="utf-8"))
        live_sources = json.loads((ROOT / "data/live/sources.json").read_text(encoding="utf-8"))
        safari_rates = json.loads((ROOT / "data/safari-rates.json").read_text(encoding="utf-8"))
        safety_rules = json.loads((ROOT / "data/safety-rules.json").read_text(encoding="utf-8"))
    except (ValueError, json.JSONDecodeError, KeyError) as error:
        fail(errors, f"Data parsing failed: {error}")
        groups, validation, pokemon, meta, roster, live, import_report, live_sources, safari_rates, safety_rules = [], {}, [], {}, [], {}, {}, {}, {}, {}

    # HTML and local assets.
    parser = IdParser()
    parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    duplicates = [name for name, count in Counter(parser.ids).items() if count > 1]
    if duplicates:
        fail(errors, f"Duplicate HTML ids: {', '.join(duplicates)}")
    for asset in parser.local_assets:
        if not (ROOT / asset).exists():
            fail(errors, f"HTML references missing asset: {asset}")

    index_text = (ROOT / "index.html").read_text(encoding="utf-8")
    if re.search(r'(?:src|href)="/', index_text):
        fail(errors, "Root-absolute HTML asset path found; GitHub project Pages requires relative paths.")

    app_text = (ROOT / "js/app.js").read_text(encoding="utf-8")
    for option in ('value="250"', 'value="500"', 'value="1000"', 'value="all"'):
        if option not in index_text:
            fail(errors, f"Expanded ranking limit option missing: {option}")
    if "appendRankingChunk" not in app_text or "IntersectionObserver" not in app_text:
        fail(errors, "Unlimited ranking mode is not using progressive rendering.")
    if "data/live/state.json" not in app_text or "loadStaticLiveState" not in app_text:
        fail(errors, "App is not wired to the same-origin live-state JSON contract.")
    if re.search(r"navigator\.serviceWorker\s*\.\s*register|serviceWorker\.register", app_text):
        fail(errors, "A service worker registration was found; WARtool must remain cache-transparent.")
    css_text = (ROOT / "css/styles.css").read_text(encoding="utf-8")
    if "v0.7 dark-contrast release" not in css_text:
        fail(errors, "Dark-mode contrast release rules are missing.")
    if "v0.7.1 dark-mode readability hotfix" not in css_text:
        fail(errors, "Dark-mode readability hotfix rules are missing.")
    for marker in ("Redirection risk", "Escape risk", "Held-item risk", "PP / Struggle", "Setup-dependent", "Needs verification", "Start delay", "safari_coverage", "safety_warnings", "slowdown_abilities", "johtoSafariRotationalTier", "greatMarshRotationalTier", "rotationalTierOptions", "safariCatchModel", "safariUnknownCatchChance", "safariCaptureFor", "expected captured points/shiny"):
        if marker not in app_text:
            fail(errors, f"Safety/slowdown UI marker missing from app.js: {marker}")
    if "encounter-slowdown.png" not in app_text:
        fail(errors, "Start-delay icon is not wired into the ranking UI.")
    for marker in ("slowdownExposure", "score-range", "100% slowed alternative", "fullDelayPointsPerHour"):
        if marker not in app_text and marker not in css_text:
            fail(errors, f"Full-slowdown alternative marker missing: {marker}")
    if "standard - exposure *" in app_text or "Delay-adjusted" in app_text or "No-delay ceiling" in app_text:
        fail(errors, "Weighted slowdown interpolation or obsolete labels are still present in app.js.")
    for method, speed in EXPECTED_METHOD_SPEEDS.items():
        pattern = rf'"{re.escape(method)}"\s*:\s*{speed}(?:\D|$)'
        if not re.search(pattern, app_text):
            fail(errors, f"Default speed missing or wrong: {method} = {speed}")

    # Core data dimensions.
    if len(pokemon) != 601:
        fail(errors, f"Expected 601 scored species, found {len(pokemon)}")
    line_count = len({item["line"] for item in pokemon}) if pokemon else 0
    if line_count != 282:
        fail(errors, f"Expected 282 evolution lines, found {line_count}")
    if len(groups) != 14985:
        fail(errors, f"Expected 14,985 display groups, found {len(groups)}")
    if int(validation.get("summary", {}).get("fatalChecks", -1)) != 0:
        fail(errors, "Encounter build reports fatal validation checks.")
    if int(validation.get("summary", {}).get("displayGroups", -1)) != len(groups):
        fail(errors, "Validation summary display-group count disagrees with data.")
    slowed_rows = [group for group in groups if "(Slowed)" in str(group.get("method", ""))]
    if slowed_rows:
        fail(errors, f"Found {len(slowed_rows)} duplicate slowed hunt rows; slowdown alternatives must stay inside the base hunt card.")
    if meta.get("siteVersion") != "0.8.11":
        fail(errors, f"Metadata siteVersion is {meta.get('siteVersion')!r}, expected '0.8.11'.")
    if (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() != "0.8.11":
        fail(errors, "VERSION.txt is not 0.8.11.")
    if "WARtool v0.8.11" not in index_text or 'APP_VERSION = "0.8.11"' not in (ROOT / "server.py").read_text(encoding="utf-8"):
        fail(errors, "Public page and local server are not consistently versioned as 0.8.11.")
    if not re.fullmatch(r"[0-9a-f]{64}", str(meta.get("encounterDumpSha256", ""))):
        fail(errors, "Encounter dump SHA-256 is missing or malformed in metadata.")

    pokemon_by_id = {int(item["id"]): item for item in pokemon}
    pokemon_by_name = {normalize(item["name"]): item for item in pokemon}
    known_lines = {item["line"] for item in pokemon}
    for item in pokemon:
        tier = int(item["tier"])
        if tier not in TIER_POINTS or int(item["points"]) != TIER_POINTS[tier]:
            fail(errors, f"Tier/point mismatch for {item['name']}: T{tier}, {item['points']} points")
        for suffix in ("", "-shiny"):
            sprite = ROOT / "assets/sprites" / f"{item['id']}{suffix}.png"
            if not sprite.is_file():
                fail(errors, f"Missing sprite: {sprite.relative_to(ROOT)}")

    methods = Counter()
    incomplete = 0
    for index, group in enumerate(groups, start=1):
        method = group.get("method")
        methods[method] += 1
        if method not in EXPECTED_METHOD_SPEEDS:
            fail(errors, f"Group {index} uses method without speed setting: {method}")
        components = group.get("components") or []
        locations = group.get("locations") or []
        if not components or not locations:
            fail(errors, f"Group {index} has no components or locations.")
            continue
        share = sum(float(component.get("share", 0)) for component in components)
        if not math.isclose(share, 1.0, rel_tol=0, abs_tol=1e-8):
            fail(errors, f"Group {index} composition sums to {share:.12f}, not 1.0")
        for component in components:
            pid = int(component.get("pokemonId", -1))
            if component.get("unknown"):
                if pid != 0 or component.get("line") != "__unknown__" or int(component.get("points", -1)) != 0:
                    fail(errors, f"Group {index} has a malformed unknown rotational component.")
                if not group.get("safari"):
                    fail(errors, f"Group {index} uses an unknown rotational component outside Safari.")
                continue
            if pid not in pokemon_by_id:
                fail(errors, f"Group {index} references unknown Pokémon id {pid}")
            if component.get("line") not in known_lines:
                fail(errors, f"Group {index} references unknown line {component.get('line')!r}")
            capture = component.get("safariCapture")
            if capture:
                if not group.get("safari"):
                    fail(errors, f"Group {index} contains Safari capture data outside a Safari method.")
                success = float(capture.get("ballsOnlySuccess", 0) or 0)
                if not (0 < success <= 1):
                    fail(errors, f"Group {index} has invalid Safari catch success {success} for {component.get('pokemon')}.")
                if capture.get("scope") not in {"Johto Safari Zone", "Sinnoh Great Marsh"}:
                    fail(errors, f"Group {index} has invalid Safari capture scope {capture.get('scope')!r}.")
        if group.get("incomplete"):
            incomplete += 1

    missing_methods = sorted(set(EXPECTED_METHOD_COUNTS) - set(methods))
    if missing_methods:
        fail(errors, f"Expected methods absent from groups: {', '.join(missing_methods)}")
    if methods != Counter(EXPECTED_METHOD_COUNTS):
        fail(errors, f"Encounter method counts changed unexpectedly: {dict(methods)}")

    valid_regions = {"Kanto", "Johto", "Hoenn", "Sinnoh", "Unova"}
    valid_types = {"Grass", "Cave", "Inside", "Water", "Dark Grass", "Old Rod", "Good Rod", "Super Rod", "Rocks", "Headbutt", "Sweet Scent", "Honey Tree", "Fossil revival"}
    for index, group in enumerate(groups, start=1):
        for location in group.get("locations", []):
            if location.get("region") not in valid_regions:
                fail(errors, f"Group {index} has non-canonical region label: {location.get('region')!r}")
            for encounter_type in location.get("encounterTypes", []):
                if encounter_type not in valid_types:
                    fail(errors, f"Group {index} has non-canonical encounter type: {encounter_type!r}")

    gate_groups = [group for group in groups if any(location.get("location") == "Safari Zone Gate" for location in group.get("locations", []))]
    if len(gate_groups) != 8 or any(group.get("method") != "Headbutt" or group.get("safari") for group in gate_groups):
        fail(errors, "Safari Zone Gate must produce exactly eight normal Headbutt groups, never Safari Singles.")

    bond_lure = [group for group in groups if group.get("method") == "Lure Singles" and any(location.get("location") == "Bond Bridge" for location in group.get("locations", []))]
    if not bond_lure or any(any(component.get("pokemon") == "Pidgeot" for component in group.get("components", [])) for group in bond_lure):
        fail(errors, "Bond Bridge lure groups still contain the obsolete Pidgeot slot.")
    if sum(any(component.get("pokemon") == "Leafeon" for component in group.get("components", [])) for group in bond_lure) != 11:
        fail(errors, "Expected Leafeon in all 11 Bond Bridge lure time/season groups.")

    zorua_groups = [
        group for group in groups
        if group.get("method") in {"3x Horde"}
        and any(location.get("location") == "Lostlorn Forest" for location in group.get("locations", []))
        and any(int(component.get("pokemonId", -1)) == 570 for component in group.get("components", []))
    ]
    if len(zorua_groups) != 7:
        fail(errors, f"Expected 7 Lostlorn Forest Zorua planner groups, found {len(zorua_groups)}.")
    for group in zorua_groups:
        zorua = next(component for component in group["components"] if int(component.get("pokemonId", -1)) == 570)
        if not math.isclose(float(zorua.get("share", 0)), 0.05, rel_tol=0, abs_tol=1e-10):
            fail(errors, f"Zorua planner share is not 5% in group {group.get('id')}.")
        if not any(note.get("code") == "temporary-unknown-rate" for note in group.get("validation", [])):
            fail(errors, f"Zorua planner group {group.get('id')} is missing its temporary-rate disclosure.")

    horde_warning_groups = [group for group in groups if any(note.get("code") == "horde-block" for note in group.get("validation", []))]
    exact_direct_groups = [
        group for group in groups
        if group.get("method") in {"3x Horde", "5x Horde"}
        and math.isclose(float(group.get("rawTotal", 0)), 1.0, rel_tol=0, abs_tol=1e-12)
    ]
    if any(any(note.get("code") == "horde-block" for note in group.get("validation", [])) for group in exact_direct_groups):
        fail(errors, "Exact 100% direct Sweet Scent tables are incorrectly marked as warnings.")
    if len(horde_warning_groups) != 7:
        fail(errors, f"Expected exactly 7 near-100% horde warning groups, found {len(horde_warning_groups)}.")
    for group in horde_warning_groups:
        if not math.isclose(float(group.get("rawTotal", 0)), 0.9999, rel_tol=0, abs_tol=1e-10):
            fail(errors, f"Unexpected horde warning total {group.get('rawTotal')} in group {group.get('id')}.")

    removed_winter_species = {"Croagunk", "Palpitoad", "Karrablast", "Shelmet", "Stunfisk"}
    corrected_winter_locations = {"Icirrus City", "Moor of Icirrus", "Route 8"}
    for group in groups:
        if group.get("season") != "Winter" or group.get("method") not in {"Singles", "Lure Singles", "5x Horde"}:
            continue
        affected_grass = [
            location for location in group.get("locations", [])
            if location.get("location") in corrected_winter_locations
            and "Grass" in location.get("encounterTypes", [])
        ]
        if not affected_grass:
            continue
        found = removed_winter_species & {component.get("pokemon") for component in group.get("components", [])}
        if found:
            fail(errors, f"Corrected winter Grass table still contains removed species: {sorted(found)}")

    # Safety, start-delay and random-encounter coverage regression checks.
    hazard_groups = [group for group in groups if group.get("hazards")]
    critical_hazard_groups = [
        group for group in groups
        if any(hazard.get("severity") == "critical" for hazard in group.get("hazards", []))
    ]
    rage_powder_groups = [
        group for group in groups
        if any(hazard.get("name") == "Rage Powder" for hazard in group.get("hazards", []))
    ]
    slowdown_groups = [group for group in groups if group.get("slowdowns")]
    natural_horde_groups = [group for group in groups if group.get("containsNaturalHordes")]
    safari_hazard_groups = [group for group in groups if group.get("safari") and group.get("hazards")]
    follow_me_groups = [
        group for group in groups
        if any(hazard.get("name") == "Follow Me" for hazard in group.get("hazards", []))
    ]
    warning_hazard_groups = [
        group for group in groups
        if any(hazard.get("severity") == "warning" for hazard in group.get("hazards", []))
    ]
    preparation_hazard_groups = [
        group for group in groups
        if any(hazard.get("severity") == "preparation" for hazard in group.get("hazards", []))
    ]
    all_hazards = [hazard for group in groups for hazard in group.get("hazards", [])]

    # Shared context-aware safety-rule contract.
    if safety_rules.get("schemaVersion") != 1:
        fail(errors, "Safety rules schemaVersion must be 1.")
    expected_categories = {"self-ko", "self-damage", "escape", "redirection", "held-item", "pp-struggle", "setup-interaction", "start-delay"}
    if set(safety_rules.get("categories", [])) != expected_categories:
        fail(errors, f"Unexpected shared safety categories: {safety_rules.get('categories')!r}")
    verification_statuses = {"confirmed", "community-documented", "needs-in-game-test"}
    if set(safety_rules.get("verificationStatuses", [])) != verification_statuses:
        fail(errors, "Shared safety verification-status list changed unexpectedly.")
    for collection_name in ("moveRules", "abilityRules", "heldItemRules", "speciesRules"):
        collection = safety_rules.get(collection_name)
        if not isinstance(collection, dict) or not collection:
            fail(errors, f"Shared safety collection {collection_name} is missing or empty.")
            continue
        for rule_name, rule in collection.items():
            missing = [key for key in ("category", "severity", "contexts", "effect", "preparation", "verification") if key not in rule]
            if missing:
                fail(errors, f"Safety rule {collection_name}.{rule_name} is missing: {', '.join(missing)}")
    if not isinstance(safety_rules.get("compoundRules"), list) or not safety_rules.get("compoundRules"):
        fail(errors, "Shared compound safety rules are missing.")
    if any(hazard.get("category") not in expected_categories - {"start-delay"} for hazard in all_hazards):
        fail(errors, "Generated hazards contain an invalid safety category.")
    if any(hazard.get("severity") not in {"critical", "warning", "preparation"} for hazard in all_hazards):
        fail(errors, "Generated hazards contain an invalid severity.")
    if any(hazard.get("verificationStatus") not in verification_statuses for hazard in all_hazards):
        fail(errors, "Generated hazards contain an invalid verification status.")
    if len(hazard_groups) != 7242:
        fail(errors, f"Expected 7,242 safety-warning groups, found {len(hazard_groups)}.")
    if len(critical_hazard_groups) != 2997:
        fail(errors, f"Expected 2,997 critical-warning groups, found {len(critical_hazard_groups)}.")
    if len(rage_powder_groups) != 88:
        fail(errors, f"Expected 88 Rage Powder multi-battle warning groups, found {len(rage_powder_groups)}.")
    rage_methods = Counter(group.get("method") for group in rage_powder_groups)
    expected_rage_methods = Counter({"Lure Singles": 50, "Singles": 27, "5x Horde": 11})
    if rage_methods != expected_rage_methods:
        fail(errors, f"Rage Powder method coverage changed unexpectedly: {dict(rage_methods)}")
    invalid_single_redirection = [
        group for group in rage_powder_groups + follow_me_groups
        if group.get("method") == "Singles"
        and not group.get("containsNaturalHordes")
        and not any("Dark Grass" in location.get("encounterTypes", []) for location in group.get("locations", []))
    ]
    if invalid_single_redirection:
        fail(errors, f"Redirection warnings leaked into {len(invalid_single_redirection)} true single-only groups.")
    if len(follow_me_groups) != 36 or any(group.get("method") != "Lure Singles" for group in follow_me_groups):
        fail(errors, f"Expected 36 Follow Me Lure-double warning groups, found {len(follow_me_groups)}.")
    if len(warning_hazard_groups) != 6088:
        fail(errors, f"Expected 6,088 warning-severity groups, found {len(warning_hazard_groups)}.")
    if len(preparation_hazard_groups) != 929:
        fail(errors, f"Expected 929 preparation groups, found {len(preparation_hazard_groups)}.")

    # 2026-08-02 safety-audit corrections.
    non_ghost_curse_species = {"Camerupt", "Ferrothorn", "Hippopotas", "Numel", "Onix", "Shelmet", "Steelix", "Turtwig"}
    leaked_curse = [hazard for hazard in all_hazards if hazard.get("name") == "Curse" and hazard.get("pokemon") in non_ghost_curse_species]
    if leaked_curse:
        fail(errors, f"Non-Ghost Curse false positives remain: {sorted({row.get('pokemon') for row in leaked_curse})}")
    curse_species = {hazard.get("pokemon") for hazard in all_hazards if hazard.get("name") == "Curse"}
    if curse_species != {"Cofagrigus", "Dusclops", "Gastly", "Shuppet", "Spiritomb"}:
        fail(errors, f"Unexpected Ghost-type Curse coverage: {sorted(curse_species)}")

    head_smash = [hazard for hazard in all_hazards if hazard.get("name") == "Head Smash"]
    if not head_smash or any("Rock-resistant" not in str(hazard.get("counter")) or "Use a Ghost-type" in str(hazard.get("counter")) for hazard in head_smash):
        fail(errors, "Head Smash advice must recommend Rock resistance and must not claim Ghost immunity.")
    memento = [hazard for hazard in all_hazards if hazard.get("name") == "Memento"]
    if not memento or any("Trapping alone does not prevent Memento" not in str(hazard.get("counter")) for hazard in memento):
        fail(errors, "Memento advice still implies that trapping alone prevents the move.")
    rage_rows = [hazard for hazard in all_hazards if hazard.get("name") == "Rage Powder"]
    follow_rows = [hazard for hazard in all_hazards if hazard.get("name") == "Follow Me"]
    if any("Extreme Speed or Feint" not in str(row.get("counter")) or "Grass types and Overcoat ignore Rage Powder" not in str(row.get("counter")) for row in rage_rows):
        fail(errors, "Rage Powder move-specific counter guidance is incomplete.")
    if not any(row.get("pokemon") in {"Hoppip", "Skiploom"} and "Worry Seed can remove it" in str(row.get("counter")) for row in rage_rows):
        fail(errors, "Hoppip/Skiploom Worry Seed caveat is missing from Rage Powder guidance.")
    if any("Extreme Speed or Feint" not in str(row.get("counter")) or "do not ignore Follow Me" not in str(row.get("counter")) for row in follow_rows):
        fail(errors, "Follow Me move-specific counter guidance is incomplete.")

    expected_new_safety_groups = {
        "Teleport": 397,
        "Sticky Barb": 61,
        "Sketch": 45,
        "Transform / Imposter preparation": 272,
        "Trick": 122,
        "Switcheroo": 16,
        "Hoppip / Skiploom compound setup": 109,
    }
    for warning_name, expected_count in expected_new_safety_groups.items():
        actual = sum(any(hazard.get("name") == warning_name for hazard in group.get("hazards", [])) for group in groups)
        if actual != expected_count:
            fail(errors, f"Expected {expected_count} groups for {warning_name}, found {actual}.")
    teleport_species = {hazard.get("pokemon") for hazard in all_hazards if hazard.get("name") == "Teleport"}
    if teleport_species != {"Abra", "Natu", "Ralts"}:
        fail(errors, f"Unexpected Teleport species coverage: {sorted(teleport_species)}")
    sticky_species = {hazard.get("pokemon") for hazard in all_hazards if hazard.get("name") == "Sticky Barb"}
    if sticky_species != {"Cacnea", "Cacturne", "Ferroseed", "Ferrothorn"}:
        fail(errors, f"Unexpected Sticky Barb species coverage: {sorted(sticky_species)}")
    for unverified_name in ("Healing Wish", "Dry Skin", "Solar Power"):
        rows = [hazard for hazard in all_hazards if hazard.get("name") == unverified_name]
        if not rows or any(row.get("severity") != "preparation" or row.get("verificationStatus") != "needs-in-game-test" for row in rows):
            fail(errors, f"{unverified_name} must remain a preparation-level, needs-verification warning.")
    for excluded_name in ("Roar", "Whirlwind", "Dragon Tail", "Circle Throw", "Destiny Bond"):
        if any(hazard.get("name") == excluded_name for hazard in all_hazards):
            fail(errors, f"Unverified mechanic {excluded_name} was added as a confirmed hazard.")
    if any(hazard.get("name") == "Perish Song" for group in groups if "Horde" in str(group.get("method")) for hazard in group.get("hazards", [])):
        fail(errors, "Perish Song warnings leaked back into explicit horde methods.")
    if safari_hazard_groups:
        fail(errors, f"Safari methods must not contain battle hazards; found {len(safari_hazard_groups)} groups.")
    if len(slowdown_groups) != 6271:
        fail(errors, f"Expected 6,271 start-delay groups, found {len(slowdown_groups)}.")
    if any(group.get("safari") and group.get("slowdowns") for group in groups):
        fail(errors, "Safari methods must not contain encounter-start ability slowdown indicators.")
    slowed_hordes = [group for group in groups if group.get("method") in {"3x Horde", "5x Horde"} and group.get("slowdowns")]
    if len(slowed_hordes) != 494:
        fail(errors, f"Expected 494 horde groups with a full-slowdown alternative, found {len(slowed_hordes)}.")
    for group in slowed_hordes:
        exposure = sum(float(component.get("share", 0)) for component in group.get("components", []) if component.get("slowAbilities"))
        if not (0 < exposure <= 1 + 1e-9):
            fail(errors, f"Invalid slowdown exposure {exposure} in group {group.get('id')}.")
    if not any(
        any(item.get("pokemonId") == 58 and "Intimidate" in item.get("abilities", []) for item in group.get("slowdowns", []))
        for group in groups
    ):
        fail(errors, "Growlithe Intimidate start-delay coverage is missing.")
    if any(
        any(item.get("pokemonId") in {228, 229} and "Unnerve" in item.get("abilities", []) for item in group.get("slowdowns", []))
        for group in groups
    ):
        fail(errors, "Hidden-ability Unnerve is incorrectly treated as a normal wild start delay for Houndour/Houndoom.")
    if len(natural_horde_groups) != 9247:
        fail(errors, f"Expected 9,247 ordinary tables containing natural hordes, found {len(natural_horde_groups)}.")
    if not any(group.get("method") == "Singles" and group.get("containsNaturalHordes") for group in groups):
        fail(errors, "Ordinary Singles no longer include natural horde rolls.")

    unknown_safari_groups = [
        group for group in groups
        if any(component.get("unknown") for component in group.get("components", []))
    ]
    if len(unknown_safari_groups) != 137:
        fail(errors, f"Expected 137 Safari groups with preserved unknown rotational mass, found {len(unknown_safari_groups)}.")
    for group in unknown_safari_groups:
        if not group.get("safari"):
            fail(errors, f"Unknown rotational mass appears outside Safari in group {group.get('id')}.")
        unknown_share = sum(float(component.get("share", 0)) for component in group.get("components", []) if component.get("unknown"))
        location_names = {location.get("location", "") for location in group.get("locations", [])}
        is_marsh = any(name.startswith("Great Marsh") for name in location_names)
        expected = 0.19 if is_marsh and group.get("lure") else 0.20 if is_marsh else 0.095 if group.get("lure") else 0.10
        if not math.isclose(unknown_share, expected, rel_tol=0, abs_tol=1e-9):
            fail(errors, f"Safari unknown rotational share is {unknown_share:.6f}, expected {expected:.3f}, in group {group.get('id')}.")
        pool = group.get("safariPool") or {}
        expected_key = "greatMarshRotationalTier" if is_marsh else "johtoSafariRotationalTier"
        if pool.get("settingKey") != expected_key:
            fail(errors, f"Safari group {group.get('id')} uses rotational setting {pool.get('settingKey')!r}, expected {expected_key!r}.")

    safari_groups = [group for group in groups if group.get("safari")]
    if len(safari_groups) != 475:
        fail(errors, f"Expected 475 Safari ranking groups after region-specific catch splitting, found {len(safari_groups)}.")
    if any(len({location.get("region") for location in group.get("locations", [])}) > 1 for group in safari_groups):
        fail(errors, "Safari groups from different regions were merged despite region-specific capture models.")
    matched_capture_groups = [
        group for group in safari_groups
        if any(component.get("safariCapture") for component in group.get("components", []))
    ]
    if len(matched_capture_groups) != 278:
        fail(errors, f"Expected 278 Safari groups with at least one matched species catch estimate, found {len(matched_capture_groups)}.")
    if any(component.get("safariCapture") for group in groups if not group.get("safari") for component in group.get("components", [])):
        fail(errors, "Safari capture estimates leaked into non-Safari groups.")
    pidgey_estimates = [
        component.get("safariCapture", {}).get("ballsOnlySuccess")
        for group in safari_groups
        for component in group.get("components", [])
        if component.get("pokemon") == "Pidgey" and component.get("safariCapture")
    ]
    if not pidgey_estimates or any(not math.isclose(float(value), 0.7392, rel_tol=0, abs_tol=1e-7) for value in pidgey_estimates):
        fail(errors, "Johto Safari Pidgey catch estimate is missing or changed from 73.92%.")
    whiscash_estimates = [
        component.get("safariCapture", {}).get("ballsOnlySuccess")
        for group in safari_groups
        for component in group.get("components", [])
        if component.get("pokemon") == "Whiscash" and component.get("safariCapture")
    ]
    if not whiscash_estimates or any(not math.isclose(float(value), 0.9773846, rel_tol=0, abs_tol=1e-7) for value in whiscash_estimates):
        fail(errors, "Great Marsh Whiscash catch estimate is missing or changed.")
    source_meta = safari_rates.get("source", {})
    if source_meta.get("strategy") != "Balls only, up to 30 Safari Balls":
        fail(errors, "Safari-rate source strategy is missing or changed.")
    if source_meta.get("name") != "ProfessorRex/HGSS-Safari-Zone" or not str(source_meta.get("url", "")).startswith("https://github.com/ProfessorRex/HGSS-Safari-Zone"):
        fail(errors, "Safari-rate source attribution is missing or changed.")
    expected_rate_counts = {"johto": 153, "sinnoh": 34}
    for region_key, expected_count in expected_rate_counts.items():
        rates = safari_rates.get(region_key)
        if not isinstance(rates, dict) or len(rates) != expected_count:
            fail(errors, f"Safari-rate table {region_key!r} contains {len(rates) if isinstance(rates, dict) else 0} entries, expected {expected_count}.")
        elif any(not (0 < float(row.get("ballsOnlySuccess", 0) or 0) <= 1) for row in rates.values()):
            fail(errors, f"Safari-rate table {region_key!r} contains an invalid balls-only success value.")

    importer_text = (ROOT / "tools/import_google_sheet.py").read_text(encoding="utf-8")
    settings_template = (ROOT / "tools/SETTINGS_SHEET_TEMPLATE.csv").read_text(encoding="utf-8-sig")
    for setting_key in ("johtoSafariRotationalTier", "greatMarshRotationalTier", "safariCatchModel", "safariUnknownCatchChance", "safariCatchChance"):
        if setting_key not in importer_text:
            fail(errors, f"Google Sheet importer does not recognize {setting_key}.")
        expected_default = {
            "johtoSafariRotationalTier": "-1",
            "greatMarshRotationalTier": "-1",
            "safariCatchModel": "1",
            "safariUnknownCatchChance": "0.52",
            "safariCatchChance": "1",
        }[setting_key]
        if f"{setting_key},{expected_default}" not in settings_template:
            fail(errors, f"Settings CSV template is missing {setting_key} default {expected_default}.")

    if "version: 9" not in app_text or "expected caught pts" not in app_text or "loss est." not in app_text:
        fail(errors, "Safari capture model migration or ranking-card labels are missing from app.js.")

    # Roster separation.
    team_counts = Counter(item.get("teamName") for item in roster if item.get("active", True))
    if team_counts != Counter({"MÜSH To My Surprise": 30, "MÜSH More Like It": 30}):
        fail(errors, f"Unexpected active roster counts: {dict(team_counts)}")
    roster_keys = [(item.get("teamId"), item.get("id")) for item in roster]
    if len(roster_keys) != len(set(roster_keys)):
        fail(errors, "Duplicate player id inside a team roster.")

    # Same-origin live-state contract and Google Sheet import pipeline.
    if live_sources.get("schemaVersion") != 1:
        fail(errors, "Live-source configuration schemaVersion must be 1.")
    configured_sources = live_sources.get("sources") if isinstance(live_sources.get("sources"), dict) else {}
    expected_gids = {"team1": "1080256717", "team2": "1113023649", "settings": "1365503836"}
    for source_name, gid in expected_gids.items():
        source = configured_sources.get(source_name) if isinstance(configured_sources.get(source_name), dict) else {}
        url = str(source.get("url", ""))
        if not re.fullmatch(rf"https://docs\.google\.com/spreadsheets/d/e/2PACX-[^?]+/pub\?[^#]*gid={gid}[^#]*output=csv[^#]*", url):
            fail(errors, f"Live source {source_name} is missing or is not the expected published CSV gid {gid}.")
    if import_report.get("schemaVersion") != 1:
        fail(errors, "Import-report schemaVersion must be 1.")
    workflow_text = (ROOT / ".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")
    if "schedule:" not in workflow_text or "tools/import_google_sheet.py" not in workflow_text:
        fail(errors, "GitHub Pages workflow is not wired to the scheduled Google Sheet importer.")
    accepted_five_minute_schedules = (
        "2-57/5 * * * *",
        "2,7,12,17,22,27,32,37,42,47,52,57 * * * *",
    )
    if not any(schedule in workflow_text for schedule in accepted_five_minute_schedules):
        fail(errors, "Expected five-minute live-data schedule is missing from the workflow.")

    if live.get("schemaVersion") != 1:
        fail(errors, f"Live-state schemaVersion must be 1, found {live.get('schemaVersion')!r}")
    if live.get("mode") not in {"preview", "demo", "live"}:
        fail(errors, f"Live-state mode must be preview, demo, or live, found {live.get('mode')!r}")
    roster_by_pair = {(item["teamId"], item["id"]): item for item in roster}
    live_catches = live.get("catches") if isinstance(live.get("catches"), list) else []
    for index, item in enumerate(live_catches, start=1):
        pid = int(item.get("pokemonId", -1))
        if pid not in pokemon_by_id:
            fail(errors, f"Live catch {index} references unknown Pokémon id {pid}")
            continue
        if item.get("line") != pokemon_by_id[pid]["line"]:
            fail(errors, f"Live catch {index} line does not match Pokémon {pokemon_by_id[pid]['name']}")
        pair = (item.get("teamId"), item.get("playerId"))
        if pair not in roster_by_pair:
            fail(errors, f"Live catch {index} player/team is not in the packaged roster: {pair}")

    packaged_total, packaged_count = score_demo_catches(live_catches, pokemon_by_id) if pokemon_by_id else (0, 0)
    if live.get("mode") == "preview" and packaged_count != 0:
        fail(errors, f"Release preview must not bundle caught shinies, found {packaged_count}.")
    preview_text = (ROOT / "data/preview.js").read_text(encoding="utf-8")
    if not re.search(r"window\.WAR_PREVIEW_CATCHES\s*=\s*\[\s*\]\s*;", preview_text):
        fail(errors, "data/preview.js still contains bundled preview catches.")

    # Local-server separation from PaxDex.
    start_bat = (ROOT / "START_WARTOOL.bat").read_text(encoding="utf-8")
    server_text = (ROOT / "server.py").read_text(encoding="utf-8")
    if "8877" not in start_bat or '"8877"' not in server_text:
        fail(errors, "WARtool dedicated local port 8877 is not consistently configured.")
    if "/__wartool_health" not in server_text:
        fail(errors, "Local server health endpoint is missing.")

    notes.extend([
        f"Pokémon: {len(pokemon)} species across {line_count} evolution lines",
        f"Ranking groups: {len(groups):,} across {len(methods)} methods",
        f"Incomplete groups hidden by default: {incomplete}",
        f"Sprites: {len(pokemon) * 2:,} normal/shiny files verified",
        f"Roster: {sum(team_counts.values())} players across {len(team_counts)} separate teams",
        f"Packaged team data: {packaged_count} catches scoring {packaged_total} points",
        "GitHub Pages paths, scheduled Google Sheet importer, and same-origin JSON contract verified",
    ])

    if errors:
        print("WARtool validation FAILED\n")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("WARtool validation PASSED\n")
    for note in notes:
        print(f"- {note}")
    print("\nMethod groups:")
    for method in EXPECTED_METHOD_SPEEDS:
        print(f"- {method}: {methods[method]:,} groups @ {EXPECTED_METHOD_SPEEDS[method]:,} encounters/hour")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
