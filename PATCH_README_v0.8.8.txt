WARtool v0.8.8 species-specific Safari catch patch

Copy everything inside this ZIP into the existing connected WarTool repository
folder and replace matching files.

Suggested commit:
Use species-specific Safari catch rates v0.8.8

The default Safari model now uses bundled community balls-only estimates for
matched Johto Safari and Great Marsh species. Unknown rotationals and unmatched
species use a 52% fallback. The optional global override remains available.

Optional published Settings rows:

safariCatchModel               1
safariUnknownCatchChance       0.52
safariCatchChance              1

Model 1 uses species estimates plus the fallback. Model 0 applies the global
safariCatchChance value to every Safari species.
