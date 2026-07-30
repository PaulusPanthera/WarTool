# Google Sheet status in WARtool v0.5

The control Sheet is retained for the upcoming live-data pipeline, but WARtool v0.5 does not fetch Google Sheets in the browser.

The planned public flow is:

Google Sheet → GitHub Action → validated JSON files → GitHub Pages

This avoids CORS problems and keeps the public website fully static.

Do not spend time connecting CSV URLs to the v0.5 visual preview. The importer will be added after the visual patch is approved and the GitHub Pages repository exists.
