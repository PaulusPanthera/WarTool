#!/usr/bin/env python3
"""Build data/live/state.json from the three published WARtool Google Sheet tabs.

The public website never contacts Google directly. This script runs in GitHub
Actions (or locally) before the static Pages artifact is built.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES_PATH = ROOT / "data/live/sources.json"
DEFAULT_STATE_PATH = ROOT / "data/live/state.json"
DEFAULT_REPORT_PATH = ROOT / "data/live/import-report.json"
TEAM1_ENV = "TEAM_SURPRISE_CSV_URL"
TEAM2_ENV = "TEAM_MORE_LIKE_IT_CSV_URL"
SETTINGS_ENV = "WAR_SETTINGS_CSV_URL"

TEAM_HEADER_ALIASES = {
    "player": ("Player", "IGN", "Name"),
    "pokemon": ("Pokemon", "Pokémon", "Species"),
    "date": ("Date", "Caught At", "CaughtAt", "Time"),
    "secret": ("Secret", "Secret Shiny"),
    "alpha": ("Alpha",),
    "safari": ("Safari",),
    "egg": ("Egg",),
    "note": ("Note", "Notes", "Location"),
}
SETTINGS_HEADER_ALIASES = {
    "setting": ("Setting", "Key", "Name"),
    "value": ("Value", "Number"),
}
KNOWN_SETTINGS = {
    "baseShinyDenominator",
    "eventWildBoost",
    "uniqueBonus",
    "secretBonus",
    "secretChance",
    "safariBonus",
    "safariCatchChance",
    "johtoSafariRotationalTier",
    "greatMarshRotationalTier",
}


class ImportFailure(RuntimeError):
    """A fatal import error that should preserve the previously deployed site."""


def normalize(value: Any) -> str:
    """Match the browser's practical name normalization for roster/species lookup."""
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower().replace("’", "'"))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9♀♂]+", "", text)


def load_window_assignment(path: Path, variable: str) -> Any:
    text = path.read_text(encoding="utf-8")
    marker = f"window.{variable}"
    start = text.find(marker)
    if start < 0:
        raise ImportFailure(f"{path.relative_to(ROOT)} does not define {marker}")
    start = text.find("=", start) + 1
    try:
        return json.JSONDecoder().raw_decode(text[start:].lstrip())[0]
    except json.JSONDecodeError as error:
        raise ImportFailure(f"Could not parse {path.relative_to(ROOT)}: {error}") from error


def bool_value(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "x", "ja", "wahr"}


def numeric_value(value: Any) -> float | int | None:
    text = str(value or "").strip().replace("\u00a0", "").replace(",", ".")
    if not text:
        return None
    percent = text.endswith("%")
    if percent:
        text = text[:-1]
    try:
        number = float(text)
    except ValueError:
        return None
    if percent:
        number /= 100
    if number.is_integer():
        return int(number)
    return number


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_date(value: Any, row_number: int) -> tuple[str, bool, bool]:
    """Return ISO timestamp, date-only flag, and missing-date flag.

    Row seconds preserve deterministic scoring order when the Sheet stores dates
    without times. Naive values use Germany's August offset (+02:00).
    """
    raw = str(value or "").strip()
    row_offset = max(0, row_number - 2)
    local_tz = timezone(timedelta(hours=2))
    if not raw:
        date = datetime(2026, 8, 1, 0, 0, 0, tzinfo=local_tz) + timedelta(seconds=row_offset)
        return date.isoformat(), True, True

    patterns: list[tuple[str, tuple[int, int, int]]] = [
        (r"^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$", (3, 2, 1)),
        (r"^(\d{1,2})/(\d{1,2})/(\d{4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$", (3, 2, 1)),
        (r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$", (1, 2, 3)),
    ]
    for pattern, order in patterns:
        match = re.match(pattern, raw)
        if not match:
            continue
        groups = match.groups()
        year = int(groups[order[0] - 1])
        month = int(groups[order[1] - 1])
        day = int(groups[order[2] - 1])
        has_time = groups[3] is not None
        hour = int(groups[3] or 0)
        minute = int(groups[4] or 0)
        second = int(groups[5] or 0)
        try:
            date = datetime(year, month, day, hour, minute, second, tzinfo=local_tz)
        except ValueError as error:
            raise ValueError(f"invalid date {raw!r}: {error}") from error
        if not has_time:
            date += timedelta(seconds=row_offset)
        return date.isoformat(), not has_time, False

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"unsupported date {raw!r}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_tz)
    return parsed.isoformat(), False, False


def validate_public_sheet_url(url: str, label: str) -> None:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError as error:
        raise ImportFailure(f"{label}: invalid URL: {error}") from error
    if parsed.scheme != "https" or parsed.hostname != "docs.google.com":
        raise ImportFailure(f"{label}: expected a published https://docs.google.com URL")
    if "/spreadsheets/d/e/" not in parsed.path or parsed.query.find("output=csv") < 0:
        raise ImportFailure(f"{label}: expected a published 2PACX CSV URL ending in output=csv")


def fetch_text(url: str, label: str, retries: int = 3, timeout: int = 30) -> str:
    validate_public_sheet_url(url, label)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "WARtool-GitHub-Importer/0.8 (+https://github.com/PaulusPanthera/WarTool)",
            "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.1",
            "Cache-Control": "no-cache",
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
                final_host = urllib.parse.urlparse(response.geturl()).hostname or ""
                if final_host not in {"docs.google.com", "doc-0s-00-sheets.googleusercontent.com"} and not final_host.endswith(".googleusercontent.com"):
                    raise ImportFailure(f"{label}: unexpected redirect host {final_host!r}")
            text = payload.decode("utf-8-sig")
            if text.lstrip().startswith("<"):
                raise ImportFailure(f"{label}: Google returned HTML instead of CSV")
            return text
        except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, ImportFailure) as error:
            last_error = error
            if attempt < retries:
                time.sleep(attempt * 2)
    raise ImportFailure(f"{label}: download failed after {retries} attempts: {last_error}")


def read_source(source: str | None, file_path: str | None, label: str) -> str:
    if file_path:
        path = Path(file_path)
        if not path.is_file():
            raise ImportFailure(f"{label}: fixture file does not exist: {path}")
        return path.read_text(encoding="utf-8-sig")
    if not source:
        raise ImportFailure(f"{label}: no source URL configured")
    return fetch_text(source, label)


def parse_csv_rows(text: str) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        raw_headers = next(reader)
    except StopIteration:
        return [], []
    headers = [normalize(header) for header in raw_headers]
    rows: list[tuple[int, dict[str, str]]] = []
    for row_number, values in enumerate(reader, start=2):
        mapped: dict[str, str] = {}
        for index, header in enumerate(headers):
            if not header or header in mapped:
                continue
            mapped[header] = values[index] if index < len(values) else ""
        rows.append((row_number, mapped))
    return headers, rows


def field_value(row: dict[str, str], aliases: Iterable[str]) -> str:
    for alias in aliases:
        key = normalize(alias)
        value = row.get(key, "")
        if str(value).strip():
            return str(value).strip()
    return ""


def has_header(headers: list[str], aliases: Iterable[str]) -> bool:
    known = set(headers)
    return any(normalize(alias) in known for alias in aliases)


def stable_catch_id(team_id: str, row_number: int, parts: Iterable[Any]) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"sheet-{team_id}-{row_number}-{digest}"


@dataclass
class TeamResult:
    label: str
    team_id: str
    team_name: str
    rows_seen: int = 0
    accepted: int = 0
    rejected: int = 0
    ignored: int = 0
    catches: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SettingsResult:
    rows_seen: int = 0
    accepted: int = 0
    rejected: int = 0
    ignored: int = 0
    settings: dict[str, Any] = field(default_factory=lambda: {"methodSpeeds": {}})
    warnings: list[str] = field(default_factory=list)


def import_team_sheet(
    text: str,
    label: str,
    team: dict[str, Any],
    roster_by_pair: dict[tuple[str, str], dict[str, Any]],
    pokemon_by_name: dict[str, dict[str, Any]],
) -> TeamResult:
    headers, rows = parse_csv_rows(text)
    if not has_header(headers, TEAM_HEADER_ALIASES["player"]) or not has_header(headers, TEAM_HEADER_ALIASES["pokemon"]):
        raise ImportFailure(f"{label}: header must contain Player and Pokemon columns")

    result = TeamResult(label=label, team_id=team["id"], team_name=team["name"])
    for row_number, row in rows:
        player_raw = field_value(row, TEAM_HEADER_ALIASES["player"])
        pokemon_raw = field_value(row, TEAM_HEADER_ALIASES["pokemon"])
        if not player_raw and not pokemon_raw:
            result.ignored += 1
            continue
        result.rows_seen += 1
        if not player_raw or not pokemon_raw:
            result.rejected += 1
            result.warnings.append(f"{label} row {row_number}: missing {'Player' if not player_raw else 'Pokemon'}")
            continue

        player_id = normalize(player_raw)
        roster_player = roster_by_pair.get((team["id"], player_id))
        if not roster_player:
            result.rejected += 1
            result.warnings.append(f"{label} row {row_number}: player {player_raw!r} is not in {team['name']}")
            continue
        pokemon = pokemon_by_name.get(normalize(pokemon_raw))
        if not pokemon:
            result.rejected += 1
            result.warnings.append(f"{label} row {row_number}: unknown Pokémon {pokemon_raw!r}")
            continue

        date_raw = field_value(row, TEAM_HEADER_ALIASES["date"])
        try:
            caught_at, date_only, date_missing = parse_date(date_raw, row_number)
        except ValueError as error:
            result.rejected += 1
            result.warnings.append(f"{label} row {row_number}: {error}")
            continue

        secret = bool_value(field_value(row, TEAM_HEADER_ALIASES["secret"]))
        alpha = bool_value(field_value(row, TEAM_HEADER_ALIASES["alpha"]))
        safari = bool_value(field_value(row, TEAM_HEADER_ALIASES["safari"]))
        egg = bool_value(field_value(row, TEAM_HEADER_ALIASES["egg"]))
        note = field_value(row, TEAM_HEADER_ALIASES["note"])
        catch_id = stable_catch_id(
            team["id"],
            row_number,
            (player_id, pokemon["id"], date_raw, secret, alpha, safari, egg, note),
        )
        result.catches.append(
            {
                "id": catch_id,
                "source": "google-sheet",
                "sheetRow": row_number,
                "playerId": player_id,
                "playerName": roster_player["name"],
                "teamId": team["id"],
                "teamName": team["name"],
                "pokemonId": int(pokemon["id"]),
                "line": pokemon["line"],
                "caughtAt": caught_at,
                "dateOnly": date_only,
                "dateMissing": date_missing,
                "secret": secret,
                "alpha": alpha,
                "safari": safari,
                "egg": egg,
                "note": note,
            }
        )
        result.accepted += 1

    if result.rows_seen > 0 and result.accepted == 0:
        raise ImportFailure(f"{label}: found {result.rows_seen} catch row(s), but none passed validation")
    return result


def import_settings_sheet(text: str, label: str) -> SettingsResult:
    headers, rows = parse_csv_rows(text)
    if not has_header(headers, SETTINGS_HEADER_ALIASES["setting"]) or not has_header(headers, SETTINGS_HEADER_ALIASES["value"]):
        raise ImportFailure(f"{label}: header must contain Setting and Value columns")
    result = SettingsResult()
    for row_number, row in rows:
        key = field_value(row, SETTINGS_HEADER_ALIASES["setting"])
        value_raw = field_value(row, SETTINGS_HEADER_ALIASES["value"])
        if not key and not value_raw:
            result.ignored += 1
            continue
        result.rows_seen += 1
        value = numeric_value(value_raw)
        if not key or value is None:
            result.rejected += 1
            result.warnings.append(f"{label} row {row_number}: missing/invalid {'Setting' if not key else 'Value'}")
            continue
        if key.startswith("method."):
            method = key[7:].strip()
            if not method:
                result.rejected += 1
                result.warnings.append(f"{label} row {row_number}: method setting has no method name")
                continue
            result.settings["methodSpeeds"][method] = value
        elif key in KNOWN_SETTINGS:
            if key in {"johtoSafariRotationalTier", "greatMarshRotationalTier"}:
                if not float(value).is_integer() or int(value) < -1 or int(value) > 7:
                    result.rejected += 1
                    result.warnings.append(f"{label} row {row_number}: {key} must be an integer from -1 to 7")
                    continue
                value = int(value)
            result.settings[key] = value
        else:
            result.rejected += 1
            result.warnings.append(f"{label} row {row_number}: unknown setting {key!r}")
            continue
        result.accepted += 1
    if not result.settings["methodSpeeds"]:
        result.settings.pop("methodSpeeds")
    if result.rows_seen > 0 and result.accepted == 0:
        raise ImportFailure(f"{label}: found settings rows, but none passed validation")
    return result


def load_sources(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ImportFailure(f"Could not read {path}: {error}") from error
    if payload.get("schemaVersion") != 1:
        raise ImportFailure(f"Unsupported sources schema in {path}")
    return payload


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES_PATH), help="Committed source configuration JSON")
    parser.add_argument("--output", default=str(DEFAULT_STATE_PATH), help="Generated live-state JSON")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Generated import report JSON")
    parser.add_argument("--team1-file", help="Offline fixture CSV for team 1")
    parser.add_argument("--team2-file", help="Offline fixture CSV for team 2")
    parser.add_argument("--settings-file", help="Offline fixture CSV for settings")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources_path = Path(args.sources)
    output_path = Path(args.output)
    report_path = Path(args.report)
    generated_at = iso_now()
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "success": False,
        "generatedAt": generated_at,
        "teams": [],
        "settings": {},
        "warnings": [],
        "fatalError": None,
    }

    try:
        sources = load_sources(sources_path)
        roster = load_window_assignment(ROOT / "data/roster.js", "WAR_ROSTER")
        pokemon = load_window_assignment(ROOT / "data/pokemon.js", "WAR_POKEMON")
        active_roster = [row for row in roster if row.get("active", True)]
        teams_by_order: dict[int, dict[str, Any]] = {}
        for player in active_roster:
            order = int(player.get("teamOrder", 99))
            teams_by_order.setdefault(order, {"id": player["teamId"], "name": player["teamName"], "order": order})
        teams = [teams_by_order[key] for key in sorted(teams_by_order)]
        if len(teams) < 2:
            raise ImportFailure("Packaged roster does not contain two competition teams")

        roster_by_pair = {(row["teamId"], row["id"]): row for row in active_roster}
        pokemon_by_name = {normalize(row["name"]): row for row in pokemon}
        # Common manual variants, though the Sheet dropdown should normally avoid them.
        for alias, pokemon_id in {
            "nidoranm": 32,
            "nidoranmale": 32,
            "nidoran♂": 32,
            "nidoranf": 29,
            "nidoranfemale": 29,
            "nidoran♀": 29,
        }.items():
            match = next((row for row in pokemon if int(row["id"]) == pokemon_id), None)
            if match:
                pokemon_by_name[normalize(alias)] = match

        source_config = sources.get("sources", {})
        team1_url = os.environ.get(TEAM1_ENV) or source_config.get("team1", {}).get("url")
        team2_url = os.environ.get(TEAM2_ENV) or source_config.get("team2", {}).get("url")
        settings_url = os.environ.get(SETTINGS_ENV) or source_config.get("settings", {}).get("url")

        team1_text = read_source(team1_url, args.team1_file, "MÜSH To My Surprise")
        team2_text = read_source(team2_url, args.team2_file, "MÜSH More Like It")
        settings_text = read_source(settings_url, args.settings_file, "WAR settings")

        team_results = [
            import_team_sheet(team1_text, "MÜSH To My Surprise", teams[0], roster_by_pair, pokemon_by_name),
            import_team_sheet(team2_text, "MÜSH More Like It", teams[1], roster_by_pair, pokemon_by_name),
        ]
        settings_result = import_settings_sheet(settings_text, "WAR settings")

        catches = [item for result in team_results for item in result.catches]
        catches.sort(key=lambda item: (item["caughtAt"], item["teamId"], item["sheetRow"], item["id"]))
        warnings = [warning for result in team_results for warning in result.warnings] + settings_result.warnings
        rejected = sum(result.rejected for result in team_results) + settings_result.rejected

        state = {
            "schemaVersion": 1,
            "mode": "live",
            "generatedAt": generated_at,
            "source": f"Google Sheets · {len(catches)} catches · {rejected} rejected rows",
            "catches": catches,
            "settings": settings_result.settings or None,
        }
        report.update(
            {
                "success": True,
                "teams": [
                    {
                        "teamId": result.team_id,
                        "teamName": result.team_name,
                        "rowsSeen": result.rows_seen,
                        "accepted": result.accepted,
                        "rejected": result.rejected,
                        "ignoredDecorativeOrBlankRows": result.ignored,
                    }
                    for result in team_results
                ],
                "settings": {
                    "rowsSeen": settings_result.rows_seen,
                    "accepted": settings_result.accepted,
                    "rejected": settings_result.rejected,
                    "ignoredDecorativeOrBlankRows": settings_result.ignored,
                },
                "warnings": warnings,
                "summary": {
                    "catches": len(catches),
                    "rejectedRows": rejected,
                    "settingsApplied": settings_result.accepted,
                },
            }
        )
        write_json_atomic(output_path, state)
        write_json_atomic(report_path, report)

        print("WARtool Google Sheet import PASSED")
        for result in team_results:
            print(f"- {result.team_name}: {result.accepted} catches, {result.rejected} rejected")
        print(f"- Settings: {settings_result.accepted} values, {settings_result.rejected} rejected")
        print(f"- Output: {output_path.relative_to(ROOT) if output_path.is_relative_to(ROOT) else output_path}")
        if warnings:
            print("\nImport warnings:")
            for warning in warnings:
                print(f"- {warning}")
        return 0
    except ImportFailure as error:
        report["fatalError"] = str(error)
        write_json_atomic(report_path, report)
        print(f"WARtool Google Sheet import FAILED\n\nERROR: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # keep a readable report for unexpected failures
        report["fatalError"] = f"Unexpected importer error: {error}"
        write_json_atomic(report_path, report)
        print(report["fatalError"], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
