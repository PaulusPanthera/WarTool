# WARtool v0.8.5 — dump(8) update

## Encounter changes

- Rebuilt the planner from `dump(8).zip`.
- 45 species have changed lure-location records in the new dump.
- Route 215 replaces the former 5% Lickilicky lure slot with Alakazam.
- Multiple lure records now point to corrected floors/sub-areas, including Rock Tunnel, Pokémon Tower, Seafoam Islands, Union Cave, Snowpoint Temple, Old Chateau and Mt. Coronet.
- Water-lure corrections automatically carry into Fishing + Lure and Fishing + Lure + Chum Bucket.
- Zorua remains modeled at the temporary requested 5% share.

## Data totals

- Display groups: **15,569 → 15,572**
- Shiny-safety warning groups: **6,748 → 6,763**
- Critical warning groups: **2,385 → 2,380**
- Warned species: **190 → 189**

| Method | v0.8.4 | v0.8.5 | Change |
|---|---:|---:|---:|
| Fishing + Lure | 919 | 923 | +4 |
| Fishing + Lure + Chum Bucket | 919 | 923 | +4 |
| Lure Singles | 3,224 | 3,219 | -5 |

## Validation

- 601 scored Pokémon and 282 evolution lines verified.
- 15,572 groups across all 16 methods verified.
- Safari safety exclusion remains enforced.
- Route 215 regression check added for Alakazam/Lickilicky.
- Exact 100% early-route Sweet Scent tables remain accepted; the 14 near-100% tables remain warnings.
- Static validator, Python compilation, JavaScript syntax check and GitHub Pages build passed.
- GitHub Pages artifact contains 1,219 files.

`dump(8).zip` SHA-256: `21c0d9dd55b171166a9f26aa7dc20d2760759bc2af0cf8de329f268cdd4747ad`
