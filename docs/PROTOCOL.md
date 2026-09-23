# Frozen experimental protocol

Frozen 2026-09-23 before model evaluation. Question: how does allowed station history change PM2.5 forecast accuracy? This is a controlled context/fitting-budget study, not a novelty or contamination-free claim.

## Cohort and time

All 12 UCI stations each serve once as the held-out target. Aotizhongxin (alphabetically first, chosen before results) is Milestone 1. Donor fitting uses the other 11 stations, 2013-03-01 through 2016-02-29. March–May 2016 is reserved for development; no target station is used in donor fitting or hyperparameter selection. Fixed LightGBM settings below are specified a priori (no search). June–August separates development from evaluation and supplies initial local fitting windows. Test origins: 2016-09-01 00:00 through 2017-02-27 23:00 Asia/Shanghai, at a fixed 25-hour stride from the start. Last target is no later than 2017-02-28 23:00. All decisions are frozen before computing test metrics.

Each model predicts the single value at origin +1, +6 and +24 hours. Chronos generates 24 steps and we retain steps 1, 6, 24. No future weather or pollutant values are supplied. Outputs are not clipped. Calendar variables at the origin are known.

## What history means (read before comparing curves)

Budgets H = 0, 24, 72, 168, 720, 2160 clock hours (0h, 1d, 3d, 7d, 30d, 90d).

* **Chronos-2:** exactly the last H target PM2.5 values through each origin, including missing values. No fitting, covariates or cross-series learning. This is zero-shot **task adaptation** at every positive budget. H=0 is not meaningful and is N/A, not a fabricated forecast. Context is explicitly set to H, including 2160 (no default 2048 truncation).
* **LightGBM global:** fit on donors only; its inference features need 24 target hours. The fitted model is identical across all positive H. No target-station labels enter fitting. At H=0 a separate calendar-only donor model forecasts without any local readings, explicitly labeled as such.
* **LightGBM global+local:** retrain the same donor model with examples from the H-hour target window ending 2016-08-31 23:00. Both the complete 24-hour feature footprint and horizon label must lie within that window. No test label enters fitting. Each local example gets weight equal to one donor station's average row count divided by the usable local example count; each donor example has weight 1. This gives the target at most one station's total weight regardless of H. If no local examples exist, use the global model and report zero fitted local samples. At H=0 use the calendar-only global model. Inference uses the latest 24 hours.
* **Persistence:** latest reading, no fitting; N/A at H=0. **Seasonal day:** observation at origin+h−24, available for H>=24. **Seasonal week:** origin+h−168, available only for H>=168. No fitting.

Crucial limitation: the x-axis is an allowed history-window length, **not total lifetime readings acquired after one physical deployment**. The conventional local model has a frozen pre-test fitting window of H hours plus rolling inference context; the FM has rolling context only. Initial fitting data and current context are different resources. Report both; do not claim equal total observation consumption or parameter fine-tuning. Earlier test observations may be used as context once observed, never to update fitted parameters. Short-feature baselines intentionally plateau when additional context is not used.

## Missingness and eligibility

One common cohort for all positive budgets, models and horizons, selected using missingness only: all three targets observed; last 24 PM2.5 readings observed; at least 90% PM2.5 observed separately in each 72/168/720/2160-hour context; each of the three week-seasonal source readings observed. Same cohort also used by the calendar-only 0h reference. Origins failing any rule are excluded, with individual flags retained. No target interpolation. Chronos handles internal NaNs natively. LightGBM handles missing covariates natively. No forward/backward filling. Report complete-case selection bias and long-gap exclusion; do not generalize to outages.

## Features and estimators

LightGBM direct model per horizon: PM2.5 lags 0,1,2,3,6,12,23; current and lag-3 PM10, SO2, NO2, CO, O3, TEMP, PRES, DEWP, RAIN, WSPM; current wind direction represented as sin/cos using the 16 compass directions; hour, weekday, month; PM2.5 rolling mean/std over 3,6,12,24 values (population std). Total 40 features, at most 24 hours of history. Calendar-only has three features. Training origins every 3 hours, with observed current value and all 24 PM2.5 historical readings and observed horizon target. Horizon labels must precede the fitting cutoff. Global and local train eligibility matches the required feature footprint. Local fitting uses every eligible hour because budgets are small.

LightGBM: squared-error regression, 200 trees, learning rate .05, 31 leaves, min_child_samples=50, max_bin=63, reg_lambda=1, deterministic=True, force_col_wise=True, 4 CPU threads, seed=20260923. No test-based tuning, early stopping, feature selection or calibration. Separate models for +1/+6/+24. Save fitted boosters.

One TSFM: public amazon/chronos-2. Resolve an immutable revision and hash weights in models/manifest.json before inference. chronos-forecasting framework, PyTorch CUDA float32, eval mode, batch size 16, cross_learning=False, prediction_length=24, context_length=H. Quantiles .1/.5/.9; point forecast is the median. Record actual package versions, parameter count, GPU, CPU and peak CUDA allocation. No second FM or fine-tuning in this benchmark. Pretraining overlap with Beijing is not ruled out.

## Metrics, uncertainty and threshold

Per horizon, station, model, budget: MAE, RMSE, bias, MASE. MASE denominator is mean absolute 24-hour seasonal difference from that station's **development-only March–May 2016** observed pairs. This scoring-only denominator is not model input and is fixed across budgets. Pooled MAE/RMSE weight station-origin pairs equally; pooled MASE averages individual errors divided by station scale. Also show per-station results and station distributions.

High PM means target > pooled 90th percentile of PM2.5 in March–May 2016 across all stations. This is a scoring-only development threshold, never a model input or regulatory/health threshold. Freeze its numeric value before inference. Report high-PM MAE, bias and count separately per horizon, plus the pooled three-horizon summary.

Chronos only: mean pinball loss across .1/.5/.9; inclusive 80% interval coverage; mean width. Report overall and high-PM separately. No distributional comparison against deterministic baselines.

History-to-threshold: earliest supported H with MAE <= 1.10 × that model's 2160h MAE **and all larger supported budgets also satisfying it**, separately by horizon, pooled and per station. Mark missing reference N/A. The sustained rule handles nonmonotonic curves. This is within-model maturity, not proof of usefulness or dominance over persistence. No interpolation between budgets.

95% confidence intervals: 2000 paired bootstrap resamples of the 12 stations, retaining each station's entire temporal sequence; compute the pooled ratio of summed absolute errors to sample count. Same sampled stations for every model/budget and for paired MAE differences against persistence. This cluster design preserves within-station serial dependence but does not account for shared citywide shocks or establish generalization outside Beijing. Milestone 1 has no station-bootstrap CI because it has one station.

## Cost and error analysis

Measure fit and synchronized inference wall time separately. Report number of donor/local fitting samples, context hours, fitted leaf counts for trees, pretrained parameter count and GPU memory; API charges zero. Checkpoint download/load and feature engineering recorded separately where practical, not silently included in steady-state inference. Shared fits/reused predictions are not charged repeatedly. Single-run timing is descriptive, not a hardware benchmark.

Inspect top 20 absolute errors per model at 90d. Use overlapping descriptive tags: rapid rise/fall (24h change >50 in magnitude), high episode, wind-direction change, temperature/pressure change, preceding missingness, forecast lag (prediction closer to origin than target), and error sign/bias. These tags describe observed associations, not atmospheric causes. No optional masking experiment until main results are complete.
