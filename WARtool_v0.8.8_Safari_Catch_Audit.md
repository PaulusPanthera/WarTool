# WARtool v0.8.8 — Safari capture-model audit

## Scope

This release replaces the former single Safari catch multiplier with a
component-weighted model.

For each possible Safari shiny species, WARtool now calculates:

```text
encounter share × catch-success chance × points if caught
```

The weighted values are summed before encounters/hour and the shiny denominator
are applied. A shiny that flees contributes zero points, including zero Safari
bonus.

## Capture models

### Model 1 — species estimates plus fallback

This is the default.

- Matched Johto Safari species use the bundled Johto estimate.
- Matched Sinnoh Great Marsh species use the bundled Sinnoh estimate.
- Unknown rotationals, unmatched species, Kanto Safari and Hoenn Safari use the
  editable fallback.
- Default fallback success: **52%**.

The 52% fallback is the rounded mean of the 187 available source entries:

- Johto table: 153 entries, 50.85% mean success.
- Sinnoh table: 34 entries, 56.57% mean success.
- Combined table: 51.89% mean success.

### Model 0 — global override

Every Safari component receives the editable `safariCatchChance` value. This is
kept for teams that prefer one conservative or optimistic assumption.

## Source and limitations

Bundled source metadata:

- Name: `ProfessorRex/HGSS-Safari-Zone`
- Strategy: `Balls only, up to 30 Safari Balls`
- URL: `https://github.com/ProfessorRex/HGSS-Safari-Zone`
- Status: community-derived estimates, not official PokeMMO documentation.

The supplied comparison package limits matching to Johto Safari and Sinnoh
Great Marsh. No equivalent species-level table was supplied for Kanto or Hoenn,
so WARtool does not invent those values.

## Generated-data results

- Total ranking groups: **17,497**.
- Safari ranking groups: **475**.
- Non-Safari groups changed by this release: **0**.
- Safari groups with at least one matched estimate: **278**.
- Safari groups using fallback only: **197**.
- Matched current encounter species:
  - Johto: 73 species.
  - Sinnoh: 16 species.
- Component occurrences:
  - Johto matched estimate: 776.
  - Sinnoh matched estimate: 327.
  - Ordinary unmatched fallback: 1,195.
  - Unknown rotational fallback: 137.

With the default 52% fallback, weighted group-level Safari success estimates
range from **36.16% to 74.29%**, with an unweighted group mean of **57.38%**.
These are location-composition estimates, not one universal Safari rate.

Regression examples:

- Johto Pidgey: 73.92% success.
- Johto Kangaskhan: 14.71% success.
- Johto Beldum: 1.16% success.
- Great Marsh Whiscash: 97.73846% success.

## Rotational interaction

The existing Safari rotational tiers remain unchanged:

- Johto unknown block: 10%, or 9.5% with Lure.
- Great Marsh unknown block: 20%, or 19% with Lure.

The selected tier determines the unknown component's score if caught. Its catch
success uses `safariUnknownCatchChance`, because its exact species is not stored
in the dump.

If the rotational remains unscored, a successful catch still has the expected
Secret Shiny value and the Safari bonus, but no assumed species-tier value.

## Settings and Sheet contract

New/active keys:

```text
safariCatchModel               1
safariUnknownCatchChance       0.52
safariCatchChance              1
```

- Model `1`: species estimates plus fallback.
- Model `0`: global override.
- Chance values must be decimals from 0 through 1.

The XLSX and CSV Settings templates contain all three rows. The Sheet importer
accepts them, rejects invalid model values, and rejects chances outside 0–1.

## UI and export checks

- Safari cards show a weighted `loss est.` badge.
- Safari cards label their secondary value as `expected caught pts`.
- The hunt dialog shows each component's catch estimate and source.
- The hunt dialog shows weighted catch success and loss.
- Ranking CSV adds catch success, loss, model and component-estimate columns.
- Safari battle-hazard and encounter-start ability warnings remain suppressed.

## Automated verification

Passed:

- Encounter rebuild from `dump(8).zip`.
- Static validator.
- Python compilation.
- JavaScript syntax check.
- Exact JavaScript `scoreGroup` execution in a Node VM:
  - species-weighted catch model;
  - 52% Kanto fallback;
  - 61% test global override;
  - weighted expected points/hour identity.
- Google Sheet importer fixtures for valid and invalid Safari settings.
- GitHub Pages build with **1,221 files**.
- Exact patch ZIP applied over a clean v0.8.7 copy, then compiled, validated and rebuilt successfully.
- Built-HTML local-reference audit.
- Non-Safari data identity against v0.8.7.

A headless Chromium navigation test was attempted, but the execution
environment blocks both localhost and file navigation with
`ERR_BLOCKED_BY_ADMINISTRATOR`. UI assets, selectors, syntax, settings wiring,
calculation functions and the exact Pages artifact were verified without that
browser navigation step.
