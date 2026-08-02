# WARtool v0.8.10 — Full slowdown alternative audit

## Intended behavior

- One ranking card per hunt.
- A 3× or 5× horde card shows a second score block only if the encounter table
  contains at least one Pokémon with a start-delay ability.
- The primary result uses the standard configured speed.
- The alternative always uses the complete `3x Horde (Slowed)` or
  `5x Horde (Slowed)` baseline.
- Encounter share does not interpolate the alternative.
- Rankings sort by the standard result.
- Safari encounters remain excluded.

## Regression examples

With standard 5× speed `1200` and slowed baseline `1000`:

- a table with 40% Intimidate exposure shows `1200` and `1000`;
- a table with 100% Intimidate exposure also shows `1200` and `1000`;
- a table without any start-delay ability shows only `1200`;
- a Safari table shows no slowdown alternative.

## Verification

- Static validator passed.
- JavaScript syntax passed.
- Python compilation passed.
- GitHub Pages artifact built with 1,221 files.
- 14,987 ranking groups retained.
- 494 horde groups contain start-delay warnings and receive the alternative.
- Zero separate `(Slowed)` ranking rows remain.
- Weighted slowdown interpolation and its old labels are rejected by the
  validator.
