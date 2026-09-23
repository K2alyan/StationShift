# What the measurements say

**Chronos-2 helps with longer-horizon forecasting when enough context is available, but this experiment does not establish that it needs less local history than a competent donor-trained LightGBM.** The global tree model is already competitive with 24 hours of local inference features and no target-station fitting. Its 90-day local retraining variant offers little pooled improvement.

The final benchmark retains 1,596 of 2,076 candidate station-origin pairs (76.9%), covering all 12 stations and three horizons. These are sparse, observed-history forecasts during September 2016–February 2017, not an outage benchmark. All supported settings share identical origins.

| Model / context | H1 MAE | H6 MAE | H24 MAE |
|---|---:|---:|---:|
| Persistence | 11.75 | 39.30 | 76.44 |
| Global LightGBM / 1d | 11.68 | 37.25 | 62.33 |
| Global+local LightGBM / 90d fitting window | 11.73 | 37.01 | 62.17 |
| Chronos-2 / 1d | 12.62 | 45.21 | 82.46 |
| Chronos-2 / 30d | 11.36 | 35.74 | 58.43 |
| Chronos-2 / 90d | 11.20 | 37.31 | 61.83 |

MAE units: µg/m³. Full metrics, per-station results and intervals are in [RESULTS](RESULTS.md). The 30d comparison is descriptive, not a context length selected on test and validated elsewhere. Chronos at 1d loses to persistence at every horizon. At 30d it improves pooled H24 MAE by 23.6% versus persistence and 6.3% versus global LightGBM. More history is not monotonically better: 90d is worse than 30d at H6 and H24.

## How much history?

Using the prospectively fixed, sustained “within 10% of own 90d MAE” rule, Chronos requires **3d at H1 and 7d at H6/H24**. Global and global+local LightGBM satisfy that rule at 1d; the latter has **zero usable local fitted examples at 1d**, so it is the global fallback. These thresholds measure each model's own maturity, not equal accuracy or total readings consumed. Seasonal/persistence thresholds mostly reflect their fixed formulas.

The budgets differ in kind: Chronos receives a rolling context window; the local tree model receives an initial pre-test fitting window plus current features. This supports a context-window comparison, not a literal day-by-day learning curve from a single deployment. The project's practical finding is therefore conditional, not evidence of universal foundation-model data efficiency.

## Variation and calibration

With Chronos's 30d context, per-station H24 MAE ranges **46.38–72.02** (station median 57.03), compared with pooled 58.43. The pooled average hides meaningful variation. All 12 station curves and the mature-budget distribution plot accompany RESULTS.md. Paired station-cluster CIs preserve within-station temporal dependence but cannot eliminate correlated citywide shocks.

Chronos's nominal 80% interval coverage at 30d context is **75.8%, 73.4%, 67.7%** at H1/H6/H24. At H24, high-PM coverage is **59.6%**, high-PM MAE **118.02**, and high-PM bias **−104.31**. The model underpredicts many extreme targets and its intervals are too narrow in aggregate. Conditional coverage on extremes is descriptive, not a requirement implied by marginal calibration. The high threshold (>168) comes only from development data and has no health interpretation. Quantile crossing is corrected without changing medians, as recorded in the protocol amendment.

## When is the foundation model worth using?

Chronos avoids task-specific fitting and yields quantiles directly. At 30d it takes **4.03 seconds** of synchronized inference across 1,596 origins and all three scored horizons on the RTX 3060, approximately **2.5 ms/origin** in batches. The global LightGBM models take **25.71 seconds** to fit all 12 holdouts × 3 horizons, then approximately **0.06 seconds** total inference on four CPU threads. Fitting can be amortized; Chronos requires the GPU here. These single-run timings exclude downloads, feature construction and startup, and do not constitute a general hardware comparison. First Chronos calls include runtime warm-up effects.

The FM is attractive when fitting infrastructure or donor training data are unavailable and a longer recent history exists, or when native quantiles are useful. The tree baseline is attractive for cheap repeated inference and short contexts. Neither these intervals nor the measured context optimum should be deployed without further validation.

## Worst cases

For each model, the top 20 absolute errors at 90d were tagged using observed variables. Of Chronos's 20 cases, **18** have high targets, **17** rapid rises, **3** rapid falls, **17** wind-direction changes and **19** lag-like forecasts. One has a historical PM2.5 gap of at least 24 hours somewhere in the 90d context; the most recent day is complete by design. Tags overlap and are not causal explanations.

The worst Chronos forecast is Aotizhongxin, origin **2017-01-27 23:00 Beijing time**, H6: observed **713**, predicted **241.39**, error **−471.61**. Observed PM2.5 rose by 704 over the target's preceding 24 hours. Another case at Gucheng, origin 2017-01-01 22:00, H6, is a rapid fall: observed 13, forecast 441.57. These illustrate lag during abrupt changes without attributing an atmospheric cause.

Global LightGBM's 20 worst cases all have high targets and underpredict them. Persistence's 20 worst cases include 16 rapid falls and 4 rapid rises. [Worst-case records](../results/worst_cases.csv) retain exact values and tags. Overall bias and high-event bias for every horizon are available in metrics.csv; the tail examples alone do not estimate systematic bias.

No second FM, fine-tuning, masking experiment, novel architecture, authorization study or publication-novelty claim was added. Pretraining overlap with Beijing remains uncertain.
