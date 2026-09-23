# ColdStartAQ

**Zero- and few-shot air-quality forecasting with time-series foundation models.**

How much station-specific history does a pretrained model need to forecast PM2.5? This compact benchmark uses the original UCI Beijing Multi-Site Air Quality dataset, leave-one-station-out LightGBM models, persistence, daily/weekly seasonal forecasts and frozen Amazon Chronos-2.

Start with [measured results](docs/RESULTS.md), [findings](docs/FINDINGS.md), or the [first milestone](docs/MILESTONE_1.md). [Dataset](docs/DATASET.md) and [frozen protocol](docs/PROTOCOL.md) explain provenance, chronological boundaries and exclusions. No model is tuned on test outcomes.

## Reproduce

Python 3.12, CUDA-capable GPU (measured on an RTX 3060 12 GB). Create a virtual environment; install the pinned dependencies. The measured PyTorch build is `2.12.1+cu126`; install its CUDA 12.6 wheel from the official PyTorch index. Exact measured versions and hardware are in `results/hardware.json`; a full installed-package snapshot is in `environment-freeze.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.12.1 --index-url https://download.pytorch.org/whl/cu126
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -c environment-freeze.txt
.\.venv\Scripts\python.exe scripts/acquire.py
.\.venv\Scripts\python.exe scripts/audit.py
.\.venv\Scripts\python.exe scripts/model_acquire.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m coldstartaq.benchmark --station Aotizhongxin
.\.venv\Scripts\python.exe -m coldstartaq.report
.\.venv\Scripts\python.exe -m coldstartaq.benchmark --all
.\.venv\Scripts\python.exe -m coldstartaq.report
.\.venv\Scripts\python.exe scripts/build_site.py
.\.venv\Scripts\python.exe -m http.server 8000 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:8000 for the results explorer. It is a static site, with no API keys, build system, remote scripts or services. It displays saved measured predictions only.

For the browser checks, install `requirements-browser.txt`, run `python -m playwright install chromium`, then run `python scripts/check_site.py` while the server is running. Desktop/mobile screenshots and the check summary are in `results/browser/`.

Acquisition downloads each archive/checkpoint once and checks SHA256 pins on later runs. Generated data and checkpoint weights are ignored; manifests are committed. Models and predictions are saved per station. Runs resume stations with `complete.json`; to recompute, archive that station's result directory first. Do not mix results from changed code, settings or checkpoints. `results/frozen.json` rejects changes to the protocol or development-derived scoring constants. Raw booster files are local artifacts and can be regenerated.

## Reading the curves correctly

History means allowed **window length**, not total lifetime sensor readings. Chronos uses H recent readings without fitting. Global LightGBM uses only donor labels plus 24 recent target readings as features. Global+local LightGBM also fits on an H-hour target window before the fixed test interval. These are different resources; the comparison is not a literal deployment-day learning trajectory or equal total acquisition budget.

0h is meaningful only for the separately labeled calendar-only donor model. Chronos remains zero-shot **task adaptation** at every positive context length. Its pretraining overlap with Beijing is uncertain. A within-model history threshold does not prove superiority to another model.

## Artifacts

* `data/manifest.json`, `models/manifest.json`: immutable source/checkpoint pins.
* `results/predictions.parquet`: every forecast, target, horizon and quantile.
* `results/metrics.csv`, `station_metrics.csv`: MAE, RMSE, MASE, bias and high-event metrics; pooled paired cluster-bootstrap CIs.
* `results/origins.csv`: every candidate with eligibility and exclusion flags.
* `results/costs.csv`, `hardware.json`: fitting/inference cost and actual sample counts.
* `results/probabilistic.csv`, `history_threshold.csv`, `worst_cases.csv`: calibration, data efficiency and observed-variable error tags.
* `results/figures/`: pooled and all station adaptation curves.

Source dataset: Song Chen (2017), [Beijing Multi-Site Air Quality, UCI](https://doi.org/10.24432/C5RK5G), CC BY 4.0. Model: [Amazon Chronos-2](https://huggingface.co/amazon/chronos-2), Apache 2.0. This project claims no novelty for PM2.5 forecasting, holdout evaluation, transfer learning or uncertainty estimation.

## Validation

The measured run passed 11 tests covering causal feature footprints, fitting-window boundaries, forecast alignment, hand-computed metric arithmetic, sustained history thresholds, paired-bootstrap behavior, identical forecast cohorts, saved-metric recomputation, saved-booster predictions and site export consistency. The saved-booster check skips on a checkout without regenerated ignored booster files.

Headless Chromium checks passed at desktop and mobile sizes, including all selectors, unavailable budgets, quantile availability, CSV download, keyboard focus, responsive overflow and failed-data loading. Evidence is saved in `results/browser/`. The in-app browser had no connection, so the browser check used locally installed standalone Chromium.
