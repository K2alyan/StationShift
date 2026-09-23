# StationShift verification

## Existing scientific checks

From the repository root, using the activated project environment:

```text
python -m pytest -q
```

The 11 existing tests cover causal feature footprints, fitting-window boundaries, forecast alignment, hand-computed metrics, sustained history thresholds, paired-bootstrap behavior, identical forecast cohorts, saved-metric recomputation, saved-booster predictions and site export consistency. The booster test skips on a checkout without regenerated, git-ignored booster files.

## Explorer checks

```text
python -m pip install -r requirements-browser.txt
python -m playwright install chromium
python scripts/build_site.py
python -m http.server 8000 --bind 127.0.0.1 --directory site
```

With the server running, use a second terminal in the same environment:

```text
python scripts/check_site.py
```

The browser script checks desktop (1440×1100) and mobile (390×844) branding and layout, page metadata, all selectors, unsupported budgets, interval availability, the project-prefixed CSV download, keyboard navigation, chart scrolling and failed-data loading. It also checks displayed MAE against measured outputs and records unexpected page/network errors. Evidence: [check summary](../results/browser/checks.json), [desktop screenshot](../results/browser/desktop.png), [mobile screenshot](../results/browser/mobile.png).

These checks use installed standalone headless Chromium. The in-app browser had no connected browser during the original verification; this is a tooling detail, not a property of the experiment.

## Rename scope

The package is `stationshift`; reproduction uses `python -m stationshift.benchmark` and `python -m stationshift.report`. No compatibility package is retained. The existing experimental protocol, amendment, model/dataset pins, predictions, metrics, figures and dependency definitions are preserved. Browser evidence is regenerated for the new branding. No models, statistical comparisons or scientific results are added by this rename.

Rename verification passed: **11 tests**, static-site rebuild, desktop/mobile browser checks, fresh-process imports, benchmark CLI help, and **23 relative links**. SHA256 comparisons confirmed **302 scientific and dependency artifacts unchanged**, including locally saved boosters, frozen protocols, measured outputs and the rebuilt site data. Source and document searches found no remaining old project-name references; Git history is preserved.

The repository root remains the existing session workspace. Rename that folder to `stationshift` from its parent after closing active servers and the workspace; recreate the virtual environment after moving it because virtual environments can contain absolute paths. This does not affect the internal package name. No remote is configured and nothing is published by this task.
