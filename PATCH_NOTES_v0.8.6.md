# WARtool v0.8.6 — encounter safety and Safari coverage

## Added

- Rage Powder and Follow Me redirection warnings for applicable horde levels.
- Start-of-battle delay indicators for normal-slot abilities such as Intimidate,
  Pressure, Unnerve, weather setters, Frisk, Download and Reactive Gas.
- Pokémon-level and hunt-level warning markers, dialog details and CSV columns.

## Corrected encounter math

- Ordinary walking, surfing and Safari tables now include naturally rolled
  3×/5× hordes and weight the result by individual Pokémon shown.
- Johto Safari grass keeps its undocumented 10% rotational/block slot.
- Great Marsh grass keeps its undocumented 20% daily-rotation slot.
- Lure versions keep 95% of the complete base pool and add the 5% lure slot,
  so unknown Safari mass becomes 9.5% or 19% respectively.
- Unknown rotational mass scores zero until its current species are known,
  making Safari points/hour a conservative lower bound instead of inflating
  the documented Pokémon to 100%.

## Deliberate limits

- Safari battle hazards remain suppressed; start-delay abilities remain visible.
- Slowdown indicators do not reduce points/hour because no stable seconds-per-
  activation measurement is available.
- Safari catch success still uses the editable global catch-success assumption;
  species-specific flee/catch modeling is not part of this patch.
