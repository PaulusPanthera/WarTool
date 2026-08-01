# WARtool v0.8.7 — mechanics and regression audit

## Redirection mechanics

Rage Powder and Follow Me are no longer limited to explicit Sweet Scent hordes.
The warning is generated only where more than one opposing wild Pokémon can be
present:

- explicit 3×/5× hordes;
- a natural horde source embedded in an ordinary encounter table;
- Dark Grass doubles;
- any non-Safari Lure method capable of opening a wild double battle.

A true single-only encounter receives no redirection warning. Lure and Dark
Grass warnings explicitly say that the move is harmless when the encounter
actually opens as a single.

Generated coverage:

- Rage Powder: 99 groups
  - Lure Singles: 50
  - ordinary Singles with natural-horde/Dark-Grass context: 27
  - 5× Horde: 11
  - 5× Horde (Slowed): 11
- Follow Me: 36 Lure Singles groups
- True single-only redirection warnings: 0

Special Lure fishing methods are re-evaluated after their method variants are
generated. The current dump contains no applicable Rage Powder/Follow Me user
in those fishing pools, but the context is now handled if future data adds one.

## Safari ability handling

Safari encounters now suppress both:

- ordinary battle hazards; and
- encounter-start ability slowdown indicators.

Verified output:

- Safari groups with battle hazards: 0
- Safari groups with ability slowdown: 0
- Non-Safari start-delay groups retained: 6,765

Lure Safari also remains exempt from redirection warnings because it does not
produce wild double encounters.

## Safari rotational tier conversion

The static dump remains incomplete for these Safari grass pools:

- Johto Safari: 10% rotational/block slot
- Great Marsh: 20% daily-rotation slot

The missing probability is never redistributed to documented Pokémon.

With Lure, the complete base pool is multiplied by 95% before the separate 5%
Lure-exclusive slot is added:

- Johto: 90% documented → 85.5%, 10% rotational → 9.5%, Lure slot → 5%
- Great Marsh: 80% documented → 76%, 20% rotational → 19%, Lure slot → 5%

Two settings convert the preserved slot to a tier estimate:

- `johtoSafariRotationalTier`
- `greatMarshRotationalTier`

Accepted values are `-1` (unscored) or Tier `0` through `7`. The tier points are
50, 45, 40, 30, 15, 10, 5 and 3 respectively.

The rotational contribution is:

```text
rotational share × selected tier value
```

It is included before the normal Safari bonus and Safari catch-success
multiplier. Because a tier alone does not identify the evolution line:

- Base, Team Live and Player Live use the selected base tier value;
- Fresh Event adds the unique-line bonus;
- All Duplicate uses one point;
- `-1` contributes zero tier/unique points.

The published Settings sheet can provide team defaults. A visitor can choose a
local browser override and later return to `Use team/default` without editing
the Sheet.

## Data and build totals

- Pokémon: 601
- Evolution lines: 282
- Ranking groups: 17,489
- Encounter methods: 16
- Safety-warning groups: 7,832
- Critical-warning groups: 2,914
- Safari groups preserving rotational mass: 137
- Johto rotational groups: 100
- Great Marsh rotational groups: 37

## Automated verification

Passed:

- Python compilation for all maintenance tools;
- JavaScript syntax check;
- static project validator;
- exact encounter rebuild from `dump(8).zip`;
- rotational scoring unit tests, including local-over-team override precedence;
- Settings CSV importer acceptance for `-1..7` and rejection of Tier 8;
- Settings workbook inspection and formula-error scan;
- GitHub Pages artifact build.

The execution environment blocked browser navigation to both localhost and file
URLs, so an interactive Chromium screenshot test could not be completed. DOM
wiring, generated data, source contracts, syntax and calculation functions were
verified independently.
