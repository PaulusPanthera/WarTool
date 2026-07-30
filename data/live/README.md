# Live team-data pipeline

The public website reads only `state.json` from its own GitHub Pages origin.

`tools/import_google_sheet.py` downloads the three public CSV sources listed in
`sources.json`, validates them against `data/roster.js` and `data/pokemon.js`,
and atomically generates:

- `state.json` — catches and calculation settings consumed by the website
- `import-report.json` — accepted/rejected row counts and readable warnings

The GitHub Pages workflow runs this importer before every deployment and on a
five-minute schedule. A failed download or structurally invalid Sheet stops the
new deployment, leaving the last successful public site untouched.

## State contract

```json
{
  "schemaVersion": 1,
  "mode": "live",
  "generatedAt": "ISO-8601 timestamp",
  "source": "human-readable source label",
  "catches": [
    {
      "id": "stable row-derived id",
      "source": "google-sheet",
      "sheetRow": 2,
      "playerId": "normalized player id",
      "playerName": "display name",
      "teamId": "normalized team id",
      "teamName": "display team name",
      "pokemonId": 1,
      "line": "Bulbasaur",
      "caughtAt": "ISO-8601 timestamp",
      "dateOnly": true,
      "dateMissing": false,
      "secret": false,
      "alpha": false,
      "safari": false,
      "egg": false,
      "note": "optional"
    }
  ],
  "settings": {
    "uniqueBonus": 8,
    "methodSpeeds": {
      "5x Horde": 1200
    }
  }
}
```

The two catch tabs are forced into their packaged teams. A player name from the
wrong roster or an unknown Pokémon is rejected and listed in the import report.
