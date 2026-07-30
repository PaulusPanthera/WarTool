# Live team-data contract

`state.json` is the only file the public website needs from the future Google Sheet pipeline.

```json
{
  "schemaVersion": 1,
  "mode": "demo or live",
  "generatedAt": "ISO-8601 timestamp",
  "source": "human-readable source label",
  "catches": [
    {
      "id": "stable unique id",
      "playerId": "normalized player id",
      "playerName": "display name",
      "teamId": "normalized team id",
      "teamName": "display team name",
      "pokemonId": 1,
      "line": "Bulbasaur",
      "caughtAt": "ISO-8601 timestamp",
      "secret": false,
      "alpha": false,
      "safari": false,
      "egg": false,
      "note": "optional"
    }
  ],
  "settings": null
}
```

The importer must validate each player against `data/roster.js` and each Pokémon/evolution line against `data/pokemon.js` before replacing this file.
