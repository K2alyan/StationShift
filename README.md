# StationShift

**Time-Series Foundation Models Under New-Station Distribution Shift**

> When does a pretrained time-series foundation model become competitive at a monitoring station held out from task-specific training?

All 12 Beijing monitoring stations are held out in turn. One pretrained model, **Chronos-2**, receives increasing target-station PM2.5 context with no task-specific fitting. **LightGBM** learns from the other 11 stations. Persistence and daily/weekly seasonal forecasts provide simple references. The experiment studies new-station transfer and context-budget effects on PM2.5 forecasts at +1, +6 and +24 hours.

## Key findings

* **Donor-trained LightGBM is already competitive with 24 hours of target-station inference history.** Its pooled +24h MAE is **62.33 µg/m³**, without target-station fitting.
* **Chronos-2 improves longer-horizon average forecasts with sufficient context.** At 30 days, its +24h MAE is **58.43 µg/m³**, versus **62.33** for global LightGBM and **76.44** for persistence. These are descriptive measured comparisons, not evidence of statistical superiority over LightGBM. More context is not uniformly better: Chronos's 90-day context performs worse at +6h and +24h than its 30-day context.
* **Pretraining did not automatically buy local-data efficiency.** Chronos reaches within 10% of its own 90-day MAE with **3d / 7d / 7d** at +1h / +6h / +24h; global LightGBM meets its corresponding within-model threshold with **1d** of inference context. This does not establish that Chronos needs less local history.
* **Long-horizon extreme-PM uncertainty is a major failure.** With 30-day context, Chronos's nominal 80% interval covers **67.7%** of +24h targets overall and only **59.6%** of high-PM targets; high-PM bias is **−104.31 µg/m³**. Lower average error does not imply calibrated uncertainty during extremes.

![Pooled context-budget curves for all 12 held-out stations, by forecast horizon](results/figures/adaptation_pooled.png)

## What is being compared?

| Strategy | Task-specific fitting | Target-station information at inference |
|---|---|---|
| Chronos-2 | None; frozen pretrained weights | H hours of PM2.5 context; no covariates |
| Global LightGBM | Other 11 stations only | 40 features spanning pollutants, weather, calendar variables and 24 hours of history |
| Global+local LightGBM | Donors plus an H-hour pre-test target-station fitting window | Same 40-feature, 24-hour inference representation |

This compares new-station transfer strategies under different information resources, not identical-input model architectures or equal data budgets. A context budget is a history-window length, **not days elapsed since deployment**. Chronos has no parameter adaptation in this experiment.

> **Scope:** one city, 12 stations, one evaluated TSFM; unknown pretraining overlap; history-window comparison rather than literal deployment age; complete-history eligibility excludes severe recent outages.

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
.\.venv\Scripts\python.exe -m stationshift.benchmark --station Aotizhongxin
.\.venv\Scripts\python.exe -m stationshift.report
.\.venv\Scripts\python.exe -m stationshift.benchmark --all
.\.venv\Scripts\python.exe -m stationshift.report
.\.venv\Scripts\python.exe scripts/build_site.py
.\.venv\Scripts\python.exe -m http.server 8000 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:8000 for the results explorer. It is a static site, with no API keys, build system, remote scripts or services. It displays saved measured predictions only.

Test commands and browser-check evidence are in [verification](docs/VERIFICATION.md).

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

The existing suite has 11 checks covering chronology, forecast alignment, metrics and saved outputs. Desktop/mobile browser checks verify the measured explorer. See [verification](docs/VERIFICATION.md) for commands, evidence and environment details. The project name, package and repository slug are `StationShift`, `stationshift` and `stationshift`, respectively.
