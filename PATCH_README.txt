WARtool v0.8.0 LIVE PIPELINE PATCH

Copy everything in this patch directly into your existing GitHub Desktop
repository folder and allow Windows to replace matching files.

Do not create a new project folder. Do not delete the existing .git folder.

After copying:
1. Open GitHub Desktop.
2. Commit with: Add live Google Sheet pipeline v0.8.0
3. Push origin.
4. Open GitHub -> Actions -> Import live data and deploy WARtool.
5. The first run verifies the three real Google CSV links and deploys the site.

The committed state stays empty. GitHub Actions generates the live state only
inside the deployment workspace, so automatic updates do not create commits.
