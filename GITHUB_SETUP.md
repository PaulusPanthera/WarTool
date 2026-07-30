# GitHub Pages and live Google Sheet setup

The repository is already structured for GitHub Desktop and GitHub Pages.

## Normal publishing workflow

1. Edit files inside the one local folder connected to GitHub Desktop.
2. Review the changes in GitHub Desktop.
3. Commit to `main`.
4. Push origin.
5. Open the repository's **Actions** tab and watch **Import live data and deploy WARtool**.

The workflow imports the current Sheet data, validates the whole project, builds
`_site`, and deploys it to GitHub Pages.

## Automatic live updates

The same workflow runs every five minutes. It does not create automated commits
or fill the Git history with generated catch data. Each run generates
`data/live/state.json` only inside the temporary deployment workspace.

A failed Sheet import stops that new deployment, so the last successful public
version stays online.

## Source configuration

The active published CSV links are committed in:

```text
data/live/sources.json
```

Because the links are public, no secret is required. Repository variables may
optionally override them under:

```text
Settings → Secrets and variables → Actions → Variables
```

Supported variable names:

```text
TEAM_SURPRISE_CSV_URL
TEAM_MORE_LIKE_IT_CSV_URL
WAR_SETTINGS_CSV_URL
```

## Manual refresh

Open:

```text
Actions → Import live data and deploy WARtool → Run workflow
```

After the run is green, reload the public website. The Caught Shinies page also
has a **Reload deployed data** button for the latest already-deployed JSON.

## Import report

The deployed report is available at:

```text
data/live/import-report.json
```

It lists accepted catches, rejected rows, settings values, and validation
warnings for the latest successful deployment.
