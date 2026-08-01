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
safariCatchModel
safariUnknownCatchChance
safariCatchChance
johtoSafariRotationalTier
greatMarshRotationalTier
```

The Safari rotational tier settings accept `-1` for unscored or an integer from
`0` through `7`. They provide the team/default estimate for the undocumented
Johto 10% and Great Marsh 20% encounter slots. Each browser can override these
two values locally from WARtool's Settings tab.

Safari catch settings:

- `safariCatchModel = 1` uses matched Johto/Great Marsh species estimates and
  `safariUnknownCatchChance` for unknown rotationals, unmatched species, Kanto
  Safari and Hoenn Safari. This is the recommended default.
- `safariCatchModel = 0` applies `safariCatchChance` globally to every Safari
  species instead.
- Chance values are decimals from `0` through `1`.

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
