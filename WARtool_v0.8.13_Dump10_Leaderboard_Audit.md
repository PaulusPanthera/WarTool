# WARtool v0.8.13 — dump(10) and leaderboard audit

## Scope

This update was applied over WARtool v0.8.12.

- Encounter source: `dump(10).zip`
- Export timestamp inside the ZIP: 2026-08-06 13:03
- SHA-256: `162992ee87eb99f4163572126c316b41379f0d574c6585c1de70161bc934c1b3`
- Leaderboard change: show scored totals and totals without bonuses

## Dump comparison

Compared with `dump(8).zip`:

- 720 monster records remain present.
- 79 Pokémon have changed location arrays.
- 258 source location records were added.
- 84 source location records were removed.
- The 84 removed records are obsolete duplicate National Park records:
  - 64 Grass records
  - 20 Headbutt records
- New records expand cave/interior, Lure, Safari and water-table coverage across the five regions.

## Generated ranking changes

| Method | v0.8.12 | v0.8.13 | Change |
|---|---:|---:|---:|
| 5x Horde | 1,887 | 1,887 | 0 |
| 3x Horde | 621 | 610 | -11 |
| Lure Singles | 3,435 | 4,356 | +921 |
| Singles | 4,174 | 4,162 | -12 |
| Safari Singles | 400 | 400 | 0 |
| Lure Safari Singles | 75 | 179 | +104 |
| Fishing | 860 | 860 | 0 |
| Fishing + Lure | 1,056 | 1,128 | +72 |
| Fishing + Chum Bucket | 860 | 860 | 0 |
| Fishing + Lure + Chum Bucket | 1,056 | 1,128 | +72 |
| Rock Smash | 256 | 256 | 0 |
| Headbutt | 257 | 245 | -12 |
| Honey Tree | 12 | 12 | 0 |
| Fossil | 36 | 36 | 0 |

Total display groups increase from 14,985 to **16,119**.

The encounter generator remains deterministic: rebuilding twice from the same
dump produced identical `data/groups.js` and `data/meta.js` hashes.

## Leaderboard no-bonus points

Each player row now displays:

- official total scored points;
- points without bonuses;
- catches;
- unique evolution lines.

The team header also displays the team total without bonuses.

“No bonus” removes:

- first evolution-line bonus;
- Secret Shiny bonus;
- Safari catch bonus.

It retains the normal base-scoring rules for:

- Alpha catches;
- Egg catches;
- same-player duplicate evolution lines.

Leaderboard ordering is unchanged and continues to use official total points.

## Validation results

Passed:

- JavaScript syntax
- Python compilation
- deterministic dump rebuild
- complete static validator
- 601 scored Pokémon
- 282 evolution lines
- 16,119 ranking groups
- 1,202 normal/shiny sprites
- Safari rotational/capture invariants
- shiny-safety and slowdown invariants
- two-team roster separation
- same-origin Google Sheet state contract
- GitHub Pages build
- 1,222 artifact files
- local server health endpoint and version
- isolated exact-source leaderboard scoring test
- isolated exact-source two-team leaderboard rendering test

The full Chromium page smoke did not complete within the container timeout while
loading the large generated dataset. No interactive-browser pass is claimed.
