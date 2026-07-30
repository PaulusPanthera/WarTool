# GitHub Pages setup

## 1. Create the repository

Create an empty GitHub repository, for example:

```text
WARtool
```

Do not initialize it with a different README or workflow if you are uploading this folder directly.

## 2. Upload the contents of `H_Wartool`

The repository root must contain:

```text
index.html
.github/
assets/
css/
data/
js/
tools/
```

Do not upload the outer ZIP or an additional `H_Wartool/H_Wartool` nesting level.

## 3. Enable GitHub Pages

Open the repository:

```text
Settings → Pages → Build and deployment → Source → GitHub Actions
```

## 4. Push to `main`

The included workflow will:

1. validate all encounter, tier, sprite, roster and live-state data
2. check `js/app.js` syntax
3. build the public `_site` directory
4. upload and deploy the GitHub Pages artifact

The first deployment normally appears under the repository's **Actions** tab.

## 5. Confirm the deployment

Open the Pages URL shown by the completed `deploy` job. Verify:

- Rankings loads
- Caught Shinies starts clean with zero bundled catches
- Tier Progress shows 282 lines
- switching between both MÜSH teams works
- the Data page reports zero fatal validation errors

## Not connected yet

Do not paste Google Sheet links into the website. The next patch will add a separate GitHub Action that reads the published Sheet tabs and writes `data/live/state.json` before deployment.
