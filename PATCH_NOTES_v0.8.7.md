# WARtool v0.8.7 — multi-battle safety and Safari rotational settings

## Rage Powder / Follow Me

- Redirection warnings now appear wherever a multi-Pokémon wild battle is possible:
  - explicit 3×/5× hordes
  - natural horde rolls inside ordinary encounter tables
  - Dark Grass doubles
  - non-Safari Lure doubles
- True single-only encounters remain warning-free.
- The warning text identifies whether the risk is conditional on a Lure double,
  Dark Grass double or natural horde.
- Special Lure fishing methods are re-evaluated after generation so their safety
  context cannot inherit a stale non-Lure result.

## Safari ability correction

- Safari encounters no longer show start-delay ability warnings.
- Safari continues to suppress all ordinary battle hazards.
- Lure Safari remains exempt from double-battle redirection warnings.

## Adjustable rotational value

Two Tier 0–7 estimates are available:

- `johtoSafariRotationalTier` for the preserved Johto 10% slot
- `greatMarshRotationalTier` for the preserved Great Marsh 20% slot

`-1` leaves the slot unscored. With a Lure, those shares remain 9.5% and 19%;
the separate Lure-exclusive slot remains 5%.

The Settings sheet can provide team defaults. Every browser can select a local
override without changing the published Sheet. Tier-only estimates cannot know
the actual evolution line, so live modes use base tier value only; Fresh Event
adds the unique-line bonus and All Duplicate scores the slot as one point.

## Verification totals

- 17,489 ranking groups
- 7,832 groups with at least one safety warning
- 2,914 groups with a critical warning
- 99 Rage Powder warning groups
- 36 Follow Me warning groups
- 6,765 non-Safari start-delay groups
- 0 Safari battle-hazard groups
- 0 Safari start-delay groups
- 137 Safari groups with preserved rotational mass
