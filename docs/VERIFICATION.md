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

The browser script checks all **1,512 selector states** at both 1440px and 390px, covering **1,044 valid measured configurations** and every unsupported combination. For each valid state it verifies MAE, RMSE, high-PM MAE, coverage, signed comparisons, interval presence, chart legend, table row count and absence of page overflow. It also checks the CSV download, measured-values keyboard toggle, focus navigation, chart scrolling and failed-data loading. Unexpected page/network errors fail the check.

Screenshots and layout checks cover [1440px](../results/browser/editorial-1440.png), [1024px](../results/browser/editorial-1024.png), [768px](../results/browser/editorial-768.png) and [390px](../results/browser/editorial-390.png). [Check summary](../results/browser/checks.json).

Display-only differences use `100 × (selected error / reference error − 1)` against global LightGBM at the exact station, horizon and context budget, only when timestamps and observed targets match and the baseline error is positive. Negative means lower error. The global model's self-comparison and unsupported comparisons are omitted. Coverage uses `100 × coverage − 80` percentage points. Browser tests compute independent expected differences from the saved data and check all supported configurations. No metric files are rewritten. The chart remains linear so zero and negative saved values retain their original meaning.

The hero is original SVG artwork generated locally from observed targets, with a shared time axis and concentration scale and artistic vertical offsets. [Asset source, attribution and license](../site/assets/README.md). It is not a photo or geographic map.

These checks use installed standalone headless Chromium. The in-app browser had no connected browser during the original verification; this is a tooling detail, not a property of the experiment.

## Rename scope

The package is `stationshift`; reproduction uses `python -m stationshift.benchmark` and `python -m stationshift.report`. No compatibility package is retained. The existing experimental protocol, amendment, model/dataset pins, predictions, metrics, figures and dependency definitions are preserved. Browser evidence is regenerated for the new branding. No models, statistical comparisons or scientific results are added by this rename.

Rename verification passed: **11 tests**, static-site rebuild, desktop/mobile browser checks, fresh-process imports, benchmark CLI help, and **23 relative links**. SHA256 comparisons confirmed **302 scientific and dependency artifacts unchanged**, including locally saved boosters, frozen protocols, measured outputs and the rebuilt site data. Source and document searches found no remaining old project-name references; Git history is preserved.

The repository root remains the existing session workspace. Rename that folder to `stationshift` from its parent after closing active servers and the workspace; recreate the virtual environment after moving it because virtual environments can contain absolute paths. This does not affect the internal package name. No remote is configured and nothing is published by this task.
