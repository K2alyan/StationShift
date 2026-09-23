# Dataset

[UCI original](https://archive.ics.uci.edu/dataset/501/beijing+multi+site+air+quality+data), DOI 10.24432/C5RK5G, Song Chen (2017), CC BY 4.0.

Retrieved 2026-09-23T21:14:31.022326+00:00. Download URL: https://archive.ics.uci.edu/static/public/501/beijing+multi+site+air+quality+data.zip

Archive SHA256: `b04da438b2f331ac0ffd45aebdfec0d20d2367feb5f6948c4b1f7ce1191e33c4`. All 12 extracted CSV SHA256 values are pinned in [manifest](../data/manifest.json). Acquisition verifies existing pins; no Kaggle data.

Verified from files: **420,768 rows; 12 stations; 35,064 hourly rows each; 2013-03-01 00:00 through 2017-02-28 23:00**. Zero duplicate station/timestamp keys, zero missing timestamps or hourly discontinuities. The files have 18 columns, including all six pollutants and six weather variables requested. PM2.5 is in micrograms per cubic metre.

Timestamps are interpreted as Beijing local civil time (Asia/Shanghai, UTC+08:00); the source has separate year/month/day/hour fields without a timezone. Parquet retains timezone-aware timestamps; time-of-day features use local time. No DST ambiguity occurs.

| station       |   rows |   observed_pm25 |   pm25_missing_pct |   longest_pm25_gap_hours |   pm25_median |   pm25_p90 |   pm25_max |
|:--------------|-------:|----------------:|-------------------:|-------------------------:|--------------:|-----------:|-----------:|
| Aotizhongxin  |  35064 |           34139 |               2.64 |                      343 |         58.00 |     188.00 |     898.00 |
| Changping     |  35064 |           34290 |               2.21 |                      167 |         46.00 |     168.00 |     882.00 |
| Dingling      |  35064 |           34285 |               2.22 |                       72 |         41.00 |     161.00 |     881.00 |
| Dongsi        |  35064 |           34314 |               2.14 |                       58 |         61.00 |     201.00 |     737.00 |
| Guanyuan      |  35064 |           34448 |               1.76 |                       71 |         59.00 |     187.30 |     680.00 |
| Gucheng       |  35064 |           34418 |               1.84 |                       54 |         60.00 |     190.00 |     770.00 |
| Huairou       |  35064 |           34111 |               2.72 |                      208 |         47.00 |     164.00 |     762.00 |
| Nongzhanguan  |  35064 |           34436 |               1.79 |                       56 |         59.00 |     197.00 |     844.00 |
| Shunyi        |  35064 |           34151 |               2.60 |                      197 |         55.00 |     184.00 |     941.00 |
| Tiantan       |  35064 |           34387 |               1.93 |                       24 |         59.00 |     189.00 |     821.00 |
| Wanliu        |  35064 |           34682 |               1.09 |                       23 |         59.00 |     191.00 |     957.00 |
| Wanshouxigong |  35064 |           34368 |               1.98 |                       43 |         60.00 |     195.00 |     999.00 |

Missing values are preserved, never interpolated from the future. Missingness by variable and station: [CSV](../results/missingness.csv). Distribution percentiles, date coverage and gap lengths: [CSV](../results/coverage.csv). These distribution summaries are descriptive, not used to select model parameters or the high-pollution threshold.

Hourly continuity does not mean observations are complete. PM2.5 observed coverage is 97.92%. Forecast exclusions are specified in PROTOCOL.md and counted in results/origins.csv.
