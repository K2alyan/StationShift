# Implementation amendment — quantile crossing

2026-09-23, after the first station report and during the initial 12-station run. Dongsi's 168-hour-context forecasts triggered an ordering assertion because the pretrained model can return crossing quantiles. This is a technical output-validity correction, not an accuracy-based model selection.

For every forecast, preserve raw q50 as the point forecast; replace q10 by min(raw q10, raw q50), and q90 by max(raw q90, raw q50). Compute interval and pinball metrics on these corrected quantiles. No target is used in the correction. Record counts of affected trajectory steps per station (all 24 steps and all five budgets, including steps not scored).

All completed stations are rerun under this rule. The original frozen protocol remains unchanged and its scoring constants are preserved. The amended run additionally pins this file's hash. Point predictions, cohorts, training and all model choices remain identical.
