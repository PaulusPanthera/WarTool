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
    "5x Horde": 1724,
    "5x Horde (Slowed)": 1724,
    "3x Horde": 610,
    "3x Horde (Slowed)": 610,
    "Lure Singles": 3224,
    "Singles": 3163,
    "Safari Singles": 392,
    "Lure Safari Singles": 75,
    "Fishing": 860,
    "Fishing + Lure": 919,
    "Fishing + Chum Bucket": 860,
    "Fishing + Lure + Chum Bucket": 919,
    "Rock Smash": 184,
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
        "data/meta.js", "data/roster.js", "data/live/state.json", "favicon.svg", "site.webmanifest",
        ".nojekyll", "server.py", "START_WARTOOL.bat", "tools/rebuild_encounters.py",
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
    except (ValueError, json.JSONDecodeError, KeyError) as error:
        fail(errors, f"Data parsing failed: {error}")
        groups, validation, pokemon, meta, roster, live = [], {}, [], {}, [], {}

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
    if "data/live/state.json" not in app_text or "loadStaticLiveState" not in app_text:
        fail(errors, "App is not wired to the same-origin live-state JSON contract.")
    if re.search(r"navigator\.serviceWorker\s*\.\s*register|serviceWorker\.register", app_text):
        fail(errors, "A service worker registration was found; WARtool must remain cache-transparent.")
    css_text = (ROOT / "css/styles.css").read_text(encoding="utf-8")
    if "v0.7 dark-contrast release" not in css_text:
        fail(errors, "Dark-mode contrast release rules are missing.")
    if "v0.7.1 dark-mode readability hotfix" not in css_text:
        fail(errors, "Dark-mode readability hotfix rules are missing.")
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
    if len(groups) != 15569:
        fail(errors, f"Expected 15,569 display groups, found {len(groups)}")
    if int(validation.get("summary", {}).get("fatalChecks", -1)) != 0:
        fail(errors, "Encounter build reports fatal validation checks.")
    if int(validation.get("summary", {}).get("displayGroups", -1)) != len(groups):
        fail(errors, "Validation summary display-group count disagrees with data.")
    if meta.get("siteVersion") != "0.7.1":
        fail(errors, f"Metadata siteVersion is {meta.get('siteVersion')!r}, expected '0.7.1'.")
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
            if pid not in pokemon_by_id:
                fail(errors, f"Group {index} references unknown Pokémon id {pid}")
            if component.get("line") not in known_lines:
                fail(errors, f"Group {index} references unknown line {component.get('line')!r}")
        if group.get("incomplete"):
            incomplete += 1

    missing_methods = sorted(set(EXPECTED_METHOD_SPEEDS) - set(methods))
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
        if group.get("method") in {"3x Horde", "3x Horde (Slowed)"}
        and any(location.get("location") == "Lostlorn Forest" for location in group.get("locations", []))
        and any(int(component.get("pokemonId", -1)) == 570 for component in group.get("components", []))
    ]
    if len(zorua_groups) != 14:
        fail(errors, f"Expected 14 Lostlorn Forest Zorua planner groups, found {len(zorua_groups)}.")
    for group in zorua_groups:
        zorua = next(component for component in group["components"] if int(component.get("pokemonId", -1)) == 570)
        if not math.isclose(float(zorua.get("share", 0)), 0.05, rel_tol=0, abs_tol=1e-10):
            fail(errors, f"Zorua planner share is not 5% in group {group.get('id')}.")
        if not any(note.get("code") == "temporary-unknown-rate" for note in group.get("validation", [])):
            fail(errors, f"Zorua planner group {group.get('id')} is missing its temporary-rate disclosure.")

    horde_warning_groups = [group for group in groups if any(note.get("code") == "horde-block" for note in group.get("validation", []))]
    exact_direct_groups = [
        group for group in groups
        if group.get("method") in {"3x Horde", "3x Horde (Slowed)", "5x Horde", "5x Horde (Slowed)"}
        and math.isclose(float(group.get("rawTotal", 0)), 1.0, rel_tol=0, abs_tol=1e-12)
    ]
    if any(any(note.get("code") == "horde-block" for note in group.get("validation", [])) for group in exact_direct_groups):
        fail(errors, "Exact 100% direct Sweet Scent tables are incorrectly marked as warnings.")
    if len(horde_warning_groups) != 14:
        fail(errors, f"Expected exactly 14 near-100% horde warning groups, found {len(horde_warning_groups)}.")
    for group in horde_warning_groups:
        if not math.isclose(float(group.get("rawTotal", 0)), 0.9999, rel_tol=0, abs_tol=1e-10):
            fail(errors, f"Unexpected horde warning total {group.get('rawTotal')} in group {group.get('id')}.")

    removed_winter_species = {"Croagunk", "Palpitoad", "Karrablast", "Shelmet", "Stunfisk"}
    corrected_winter_locations = {"Icirrus City", "Moor of Icirrus", "Route 8"}
    for group in groups:
        if group.get("season") != "Winter" or group.get("method") not in {"Singles", "Lure Singles", "5x Horde", "5x Horde (Slowed)"}:
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

    # Roster separation.
    team_counts = Counter(item.get("teamName") for item in roster if item.get("active", True))
    if team_counts != Counter({"MÜSH To My Surprise": 30, "MÜSH More Like It": 30}):
        fail(errors, f"Unexpected active roster counts: {dict(team_counts)}")
    roster_keys = [(item.get("teamId"), item.get("id")) for item in roster]
    if len(roster_keys) != len(set(roster_keys)):
        fail(errors, "Duplicate player id inside a team roster.")

    # Same-origin live-state contract.
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
        "GitHub Pages paths, no-cache local server, and JSON live-data contract verified",
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
