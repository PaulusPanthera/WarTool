# Google Sheet control panel

WARtool uses three separately published CSV tabs:

1. `MÜSH To My Surprise`
2. `MÜSH More Like It`
3. `Settings`

The active links are stored in `data/live/sources.json`.

## Catch tab columns

```text
Date | Player | Pokemon | Secret | Alpha | Safari | Egg | Note
```

- Add one row per caught shiny.
- `Date` is optional; `DD.MM.YYYY` is supported.
- Player names must belong to that tab's packaged 30-player roster.
- Pokémon names must match the Sheet dropdown or packaged species data.
- Checkbox values may be `TRUE/FALSE`; blank means false.
- Decorative text outside these named columns is ignored.

The tab decides the team. There is intentionally no Team column.

## Settings tab columns

```text
Setting | Value
```

Supported base keys:

```text
baseShinyDenominator
eventWildBoost
uniqueBonus
secretBonus
secretChance
safariBonus
safariCatchChance
```

Encounter speeds use the prefix `method.`, for example:

```text
method.5x Horde | 1200
method.3x Horde | 720
```

## Validation behavior

- A failed download or missing required headers stops deployment.
- Unknown player/Pokémon rows are skipped and reported.
- If a non-empty team tab has no valid catch rows, deployment stops.
- Blank and decorative rows are ignored.
- The public site remains on the last successful deployment after a failed run.
