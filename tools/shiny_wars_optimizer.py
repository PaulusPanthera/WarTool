#!/usr/bin/env python3
"""PokeMMO Shiny Wars 2026 spot optimizer.

Usage:
    python shiny_wars_optimizer.py dump.zip --out optimizer_output
    python shiny_wars_optimizer.py dump.zip --config optimizer_config.json --out optimizer_output

Uses only the Python standard library. It reads info/monsters.json from a PokeMMO
moddable-resource dump and exports ranked CSV/JSON files.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import zipfile
from pathlib import Path
from typing import Any

TIER_POINTS = {0: 50, 1: 45, 2: 40, 3: 30, 4: 15, 5: 10, 6: 5, 7: 3}

# Current 2026 tier chart, one representative per scoring evolution line.
TIER_LISTS = {
    0: "Bulbasaur|Charmander|Squirtle|Eevee|Porygon|Snorlax|Chikorita|Cyndaquil|Totodile|Togepi|Tyrogue|Treecko|Torchic|Mudkip|Shedinja|Beldum|Turtwig|Chimchar|Piplup|Riolu|Rotom|Snivy|Tepig|Oshawott".split("|"),
    1: "Chansey|Kangaskhan|Scyther|Pinsir|Sudowoodo|Skarmory|Shroomish|Slakoth|Skitty|Plusle|Minun|Gulpin|Castform|Absol|Burmy|Combee|Cherubi|Spiritomb|Skorupi|Carnivine|Pansage|Pansear|Panpour|Drilbur|Audino|Ducklett|Emolga|Alomomola|Larvesta".split("|"),
    2: "Clefairy|Shellder|Mr. Mime|Lapras|Omanyte|Kabuto|Aerodactyl|Aipom|Pineco|Qwilfish|Shuckle|Corsola|Houndour|Miltank|Ralts|Nincada|Lileep|Anorith|Feebas|Relicanth|Bagon|Cranidos|Shieldon|Tirtouga|Archen|Zorua|Pawniard".split("|"),
    3: "Vulpix|Growlithe|Farfetch'd|Exeggcute|Staryu|Jynx|Magmar|Tauros|Dratini|Sentret|Ledyba|Sunkern|Yanma|Murkrow|Misdreavus|Gligar|Heracross|Remoraid|Delibird|Mantine|Nosepass|Volbeat|Illumise|Carvanha|Wailmer|Cacnea|Zangoose|Seviper|Barboach|Kecleon|Tropius|Chimecho|Luvdisc|Drifloon|Stunky|Chatot|Gible|Croagunk|Finneon|Darumaka|Maractus|Sigilyph|Cryogonal".split("|"),
    4: "Oddish|Venonat|Meowth|Drowzee|Electabuzz|Hoothoot|Spinarak|Wooper|Snubbull|Sneasel|Larvitar|Lotad|Surskit|Spinda|Trapinch|Lunatone|Corphish|Kricketot|Pachirisu|Buneary|Purrloin|Pidove|Scraggy|Axew|Bouffalant|Rufflet|Heatmor|Deino".split("|"),
    5: "Caterpie|Weedle|Pikachu|Nidoran♂|Jigglypuff|Paras|Bellsprout|Horsea|Natu|Hoppip|Teddiursa|Wurmple|Taillow|Numel|Swablu|Snorunt|Starly|Hippopotas|Lillipup|Timburr|Throh|Sawk|Venipede|Cottonee|Petilil|Dwebble|Trubbish|Foongus|Karrablast|Joltik|Ferroseed|Tynamo|Cubchoo|Shelmet".split("|"),
    6: "Pidgey|Spearow|Ekans|Nidoran♀|Diglett|Mankey|Abra|Ponyta|Doduo|Grimer|Cubone|Lickitung|Tangela|Ditto|Chinchou|Mareep|Slugma|Phanpy|Stantler|Poochyena|Zigzagoon|Wingull|Whismur|Makuhita|Sableye|Mawile|Aron|Electrike|Roselia|Solrock|Spoink|Clamperl|Bidoof|Shinx|Snover|Patrat|Munna|Blitzle|Roggenrola|Woobat|Tympole|Sewaddle|Minccino|Gothita|Solosis|Vanillite|Klink|Elgyem|Stunfisk|Druddigon|Vullaby|Durant".split("|"),
    7: "Rattata|Sandshrew|Zubat|Psyduck|Poliwag|Machop|Tentacool|Geodude|Slowpoke|Magnemite|Seel|Gastly|Onix|Krabby|Voltorb|Koffing|Rhyhorn|Goldeen|Magikarp|Marill|Unown|Wobbuffet|Girafarig|Dunsparce|Swinub|Smeargle|Seedot|Meditite|Torkoal|Baltoy|Shuppet|Duskull|Spheal|Buizel|Shellos|Glameow|Bronzor|Basculin|Sandile|Yamask|Deerling|Frillish|Litwick|Mienfoo|Golett".split("|"),
}

DEFAULT_CONFIG: dict[str, Any] = {
    "base_shiny_denominator": 30000.0,
    "event_wild_shiny_boost": 0.10,
    "unique_bonus": 8.0,
    "secret_bonus": 20.0,
    "secret_probability_given_shiny": 0.0625,
    "safari_bonus": 10.0,
    "safari_catch_success": 1.0,
    "lure_exclusive_share": 0.05,
    "encounters_per_hour": {
        "5x Horde": 1200.0,
        "5x Horde (Slowed)": 1000.0,
        "3x Horde": 720.0,
        "3x Horde (Slowed)": 600.0,
        "Lure Singles": 280.0,
        "Singles": 220.0,
        "Safari Singles": 300.0,
        "Lure Safari Singles": 300.0,
        "Fishing": 270.0,
        "Fishing + Lure": 340.0,
        "Fishing + Chum Bucket": 400.0,
        "Fishing + Lure + Chum Bucket": 500.0,
        "Rock Smash": 120.0,
        "Headbutt": 120.0,
        "Honey Tree": 60.0,
        "Fossil": 120.0,
    },
}

SEASONS = ("Spring", "Summer", "Autumn", "Winter")
WEEK_BY_SEASON = {
    "Summer": "Week 1 · Aug 1–7",
    "Autumn": "Week 2 · Aug 8–14",
    "Winter": "Week 3 · Aug 15–21",
    "Spring": "Week 4 · Aug 22–28",
}
TIMES = (("Morning", "rarity_morning"), ("Day", "rarity_day"), ("Night", "rarity_night"))


def normalize_name(value: str) -> str:
    value = value.strip().lower().replace("é", "e").replace("’", "'")
    aliases = {
        "nidoran [m]": "nidoran♂", "nidoran m": "nidoran♂", "nidoran male": "nidoran♂",
        "nidoran [f]": "nidoran♀", "nidoran f": "nidoran♀", "nidoran female": "nidoran♀",
        "mr mime": "mr. mime", "farfetchd": "farfetch'd",
    }
    value = aliases.get(value, value)
    value = value.replace("♀", "female").replace("♂", "male")
    return re.sub(r"[^a-z0-9]+", "", value)


class DSU:
    def __init__(self, values: list[int]):
        self.parent = {value: value for value in values}

    def find(self, value: int) -> int:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def load_monsters(dump_zip: Path) -> list[dict[str, Any]]:
    if not dump_zip.exists():
        raise FileNotFoundError(f"Dump not found: {dump_zip}")
    with zipfile.ZipFile(dump_zip) as archive:
        try:
            raw = archive.read("info/monsters.json")
        except KeyError as exc:
            raise ValueError("The ZIP does not contain info/monsters.json") from exc
    monsters = json.loads(raw.decode("utf-8"), strict=False)
    for monster in monsters:
        for location in monster.get("locations", []):
            region_text = str(location.get("region_name", ""))
            region_match = re.search(r"\[\s*([^\]]+?)\s*\]", region_text)
            if region_match:
                location["region_name"] = region_match.group(1).strip()
            type_text = str(location.get("type", ""))
            for known_type in ("Super Rod", "Good Rod", "Old Rod", "Dark Grass", "Sweet Scent", "Honey Tree", "Dust Cloud", "Headbutt", "Fishing", "Shadow", "Inside", "Grass", "Cave", "Water", "Rocks"):
                if type_text.endswith(known_type):
                    location["type"] = known_type
                    break
    if not isinstance(monsters, list) or not monsters:
        raise ValueError("info/monsters.json is empty or invalid")
    return monsters


def merge_config(path: Path | None) -> dict[str, Any]:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if path is None:
        return config
    supplied = json.loads(path.read_text(encoding="utf-8"))
    for key, value in supplied.items():
        if key == "encounters_per_hour":
            config[key].update(value)
        else:
            config[key] = value
    return config


def build_tier_mapping(monsters: list[dict[str, Any]]) -> tuple[dict[int, int], dict[int, str]]:
    canonical = [monster for monster in monsters if 1 <= monster["id"] <= 649]
    by_id = {monster["id"]: monster for monster in canonical}
    by_name: dict[str, list[int]] = collections.defaultdict(list)
    for monster in canonical:
        by_name[normalize_name(monster["name"])].append(monster["id"])

    dsu = DSU(list(by_id))
    for monster in canonical:
        for evolution in monster.get("evolutions", []):
            target = evolution.get("id")
            if target not in by_id:
                continue
            # Shiny Wars lists Shedinja separately from the Nincada/Ninjask line.
            if monster["id"] == 290 and target == 292:
                continue
            dsu.union(monster["id"], target)

    root_entries: dict[int, list[tuple[int, str, int]]] = collections.defaultdict(list)
    for tier, names in TIER_LISTS.items():
        for name in names:
            ids = by_name.get(normalize_name(name), [])
            if not ids:
                raise ValueError(f"Tier-list species was not found in monsters.json: {name}")
            monster_id = ids[0]
            root_entries[dsu.find(monster_id)].append((tier, name, monster_id))

    conflicts = {
        root: values for root, values in root_entries.items()
        if len({value[0] for value in values}) > 1
    }
    if conflicts:
        raise ValueError(f"Conflicting tiers in evolution components: {conflicts}")

    tier_by_id: dict[int, int] = {}
    line_by_id: dict[int, str] = {}
    for monster_id in by_id:
        values = root_entries.get(dsu.find(monster_id), [])
        if values:
            tier_by_id[monster_id] = values[0][0]
            line_by_id[monster_id] = values[0][1]

    tier_by_id[292] = 0
    line_by_id[292] = "Shedinja"

    located_without_tier = [
        monster["name"] for monster in canonical
        if monster.get("locations") and monster["id"] not in tier_by_id
    ]
    if located_without_tier:
        raise ValueError(f"Located Pokémon without a Shiny Wars tier: {located_without_tier}")
    return tier_by_id, line_by_id


def parse_percent(value: Any) -> float | None:
    if isinstance(value, str) and value.endswith("%"):
        return float(value[:-1]) / 100.0
    return None


def is_safari(location: dict[str, Any]) -> bool:
    text = f"{location.get('location_name_full', '')} {location.get('location_name', '')}".lower()
    return "safari zone gate" not in text and ("safari zone" in text or "great marsh" in text)


def classify_method(location: dict[str, Any]) -> str | None:
    if location.get("is_horde_5x"):
        return "5x Horde"
    if location.get("is_horde_3x"):
        return "3x Horde"
    if is_safari(location):
        return "Safari Singles"
    encounter_type = location.get("type")
    if encounter_type in {"Grass", "Cave", "Inside", "Water", "Dark Grass"}:
        return "Singles"
    if encounter_type in {"Old Rod", "Good Rod", "Super Rod"}:
        return "Fishing"
    if encounter_type == "Rocks":
        return "Rock Smash"
    if encounter_type == "Headbutt":
        return "Headbutt"
    if encounter_type == "Honey Tree":
        return "Honey Tree"
    return None


def secret_eligible(method: str) -> bool:
    return "Horde" not in method


def build_rankings(
    monsters: list[dict[str, Any]],
    tier_by_id: dict[int, int],
    line_by_id: dict[int, str],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    numeric_groups: dict[tuple[Any, ...], list[tuple[float, dict[str, Any], dict[str, Any], str]]] = collections.defaultdict(list)
    lure_groups: dict[tuple[Any, ...], list[tuple[dict[str, Any], dict[str, Any]]]] = collections.defaultdict(list)

    for monster in monsters:
        monster_id = monster["id"]
        if monster_id not in tier_by_id:
            continue
        tier = tier_by_id[monster_id]
        for location in monster.get("locations", []):
            method = classify_method(location)
            if method is None:
                continue
            seasons = SEASONS if location.get("season") == "Any" else (location.get("season"),)
            for season in seasons:
                for time_name, time_field in TIMES:
                    value = location.get(time_field, "--")
                    key = (
                        location["region_name"], location["location_id"], location["location_name_full"],
                        location["type"], season, time_name,
                        bool(location.get("is_horde_3x")), bool(location.get("is_horde_5x")),
                        location.get("rarity_flags", 0),
                    )
                    species = {
                        "pokemon_id": monster_id,
                        "pokemon": monster["name"],
                        "form": location.get("form", -1),
                        "tier": tier,
                        "tier_points": TIER_POINTS[tier],
                        "line": line_by_id[monster_id],
                        "catch_rate": monster.get("catch_rate"),
                        "min_level": location.get("min_level"),
                        "max_level": location.get("max_level"),
                    }
                    probability = parse_percent(value)
                    if probability is not None:
                        numeric_groups[key].append((probability, species, location, method))
                    elif value == "Lure":
                        lure_key = (
                            location["region_name"], location["location_id"], location["location_name_full"],
                            location["type"], season, time_name,
                        )
                        lure_groups[lure_key].append((species, location))

    effective_denominator = config["base_shiny_denominator"] / (1.0 + config["event_wild_shiny_boost"])
    rows: list[dict[str, Any]] = []

    for key, entries in numeric_groups.items():
        region, location_id, location_name, encounter_type, season, time_name, horde_3x, horde_5x, rarity_flags = key
        method = entries[0][3]
        raw_total = sum(entry[0] for entry in entries)
        if raw_total <= 0:
            continue

        incomplete = False
        warning = ""
        if not (horde_3x or horde_5x) and raw_total < 0.94:
            incomplete = True
            warning = f"Numeric table totals {raw_total:.2%}; rotating/special slots are not fully represented."

        base_probabilities = [entry[0] / raw_total for entry in entries]
        variants: list[tuple[str, list[float], list[tuple[Any, ...]], bool]] = [
            (method, base_probabilities, list(entries), False)
        ]

        lure_key = (region, location_id, location_name, encounter_type, season, time_name)
        lure_species = lure_groups.get(lure_key, [])
        if method in {"Singles", "Safari Singles"} and lure_species:
            lure_share = float(config["lure_exclusive_share"])
            combined_probabilities = [probability * (1.0 - lure_share) for probability in base_probabilities]
            lure_probability = lure_share / len(lure_species)
            combined_entries = list(entries)
            for species, location in lure_species:
                combined_entries.append((lure_probability, species, location, "Lure Singles"))
                combined_probabilities.append(lure_probability)
            lure_method = "Lure Safari Singles" if method == "Safari Singles" else "Lure Singles"
            variants.append((lure_method, combined_probabilities, combined_entries, True))

        for variant_method, probabilities, variant_entries, lure_variant in variants:
            encounters_per_hour = float(config["encounters_per_hour"].get(variant_method, 0.0))
            if encounters_per_hour <= 0:
                continue

            line_probabilities: dict[str, float] = collections.defaultdict(float)
            species_probabilities: dict[str, float] = collections.defaultdict(float)
            species_metadata: dict[str, dict[str, Any]] = {}
            weighted_tier_points = 0.0
            for probability, entry in zip(probabilities, variant_entries):
                species = entry[1]
                weighted_tier_points += probability * species["tier_points"]
                line_probabilities[species["line"]] += probability
                species_probabilities[species["pokemon"]] += probability
                species_metadata[species["pokemon"]] = species

            secret_ev = (
                float(config["secret_bonus"]) * float(config["secret_probability_given_shiny"])
                if secret_eligible(variant_method) else 0.0
            )
            safari = is_safari(variant_entries[0][2])
            safari_bonus = float(config["safari_bonus"]) if safari else 0.0
            average_no_unique = weighted_tier_points + secret_ev + safari_bonus
            average_fresh = average_no_unique + float(config["unique_bonus"])
            catch_multiplier = float(config["safari_catch_success"]) if safari else 1.0

            species_sorted = sorted(species_probabilities.items(), key=lambda item: (-item[1], item[0]))
            composition = "; ".join(
                f"{name} {probability:.1%} (T{species_metadata[name]['tier']})"
                for name, probability in species_sorted[:12]
            )
            component_rows = [
                {
                    "pokemon": name,
                    "share": probability,
                    "tier": species_metadata[name]["tier"],
                    "tier_points": species_metadata[name]["tier_points"],
                    "line": species_metadata[name]["line"],
                }
                for name, probability in species_sorted
            ]

            rows.append({
                "region": region,
                "location": location_name,
                "location_id": location_id,
                "week": WEEK_BY_SEASON.get(season, season),
                "season": season,
                "time": time_name,
                "encounter_type": encounter_type,
                "method": variant_method,
                "safari": safari,
                "lure_variant": lure_variant,
                "incomplete_table": incomplete,
                "unique_lines": len(line_probabilities),
                "avg_tier_points": weighted_tier_points,
                "encounters_per_hour": encounters_per_hour,
                "expected_secret_bonus": secret_ev,
                "safari_bonus": safari_bonus,
                "avg_points_no_unique": average_no_unique,
                "avg_points_fresh": average_fresh,
                "expected_points_per_hour_no_unique": encounters_per_hour / effective_denominator * average_no_unique * catch_multiplier,
                "expected_points_per_hour_fresh": encounters_per_hour / effective_denominator * average_fresh * catch_multiplier,
                "expected_points_per_hour_all_duplicate": encounters_per_hour / effective_denominator * (1.0 + secret_ev + safari_bonus) * catch_multiplier,
                "top_target": species_sorted[0][0],
                "top_target_share": species_sorted[0][1],
                "composition": composition,
                "raw_rate_total": raw_total,
                "warning": warning,
                "_components": component_rows,
            })

    rows.sort(key=lambda row: (
        row["incomplete_table"],
        -row["expected_points_per_hour_fresh"],
        row["region"], row["location"], row["season"], row["time"], row["method"],
    ))

    components: list[dict[str, Any]] = []
    complete_rank = 0
    for spot_id, row in enumerate(rows, start=1):
        row["spot_id"] = spot_id
        if not row["incomplete_table"]:
            complete_rank += 1
            row["default_rank"] = complete_rank
        else:
            row["default_rank"] = ""
        for component in row.pop("_components"):
            components.append({
                "spot_id": spot_id,
                "region": row["region"],
                "location": row["location"],
                "location_id": row["location_id"],
                "season": row["season"],
                "time": row["time"],
                "method": row["method"],
                **component,
            })
    return rows, components


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export_results(
    out_dir: Path,
    monsters: list[dict[str, Any]],
    tier_by_id: dict[int, int],
    line_by_id: dict[int, str],
    rankings: list[dict[str, Any]],
    components: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "rankings.csv", rankings)
    write_csv(out_dir / "spot_components.csv", components)

    tier_rows = []
    by_id = {monster["id"]: monster for monster in monsters}
    for monster_id in sorted(tier_by_id):
        tier = tier_by_id[monster_id]
        tier_rows.append({
            "pokemon_id": monster_id,
            "pokemon": by_id[monster_id]["name"],
            "line": line_by_id[monster_id],
            "tier": tier,
            "points": TIER_POINTS[tier],
        })
    write_csv(out_dir / "tier_mapping.csv", tier_rows)

    (out_dir / "optimizer_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    metadata = {
        "monsters_in_dump": len(monsters),
        "tiered_species_ids": len(tier_by_id),
        "ranking_variants": len(rankings),
        "complete_variants": sum(not row["incomplete_table"] for row in rankings),
        "incomplete_variants": sum(row["incomplete_table"] for row in rankings),
        "methodology": {
            "hordes": "Rates are normalized conditionally inside each 3x/5x horde table.",
            "lures": "A 5% total lure-exclusive slot is split equally when a location has multiple lure-exclusive species.",
            "special_tables": "Numeric encounter groups below 94% total are flagged incomplete and sorted after complete groups.",
            "safari": "The global safari catch-success input defaults to 100%; species-specific flee/catch modeling is not included.",
            "not_ranked": "Alpha schedules, legendary/mythical encounters, phenomena/special encounters, eggs, fossils, Game Corner and chum-specific tables are not ranked.",
        },
    }
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank PokeMMO Shiny Wars 2026 hunting spots")
    parser.add_argument("dump_zip", type=Path, help="PokeMMO dump ZIP containing info/monsters.json")
    parser.add_argument("--config", type=Path, help="Optional optimizer_config.json override")
    parser.add_argument("--out", type=Path, default=Path("optimizer_output"), help="Output folder")
    args = parser.parse_args()

    config = merge_config(args.config)
    monsters = load_monsters(args.dump_zip)
    tier_by_id, line_by_id = build_tier_mapping(monsters)
    rankings, components = build_rankings(monsters, tier_by_id, line_by_id, config)
    export_results(args.out, monsters, tier_by_id, line_by_id, rankings, components, config)

    complete = sum(not row["incomplete_table"] for row in rankings)
    print(f"Created {len(rankings):,} ranking variants ({complete:,} complete) in {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
