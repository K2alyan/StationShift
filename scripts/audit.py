"""Validate every station, preserving missing values and normalizing local timestamps."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VARIABLES = ['PM2.5','PM10','SO2','NO2','CO','O3','TEMP','PRES','DEWP','RAIN','wd','WSPM']

def main():
    out = ROOT / 'data/processed'
    out.mkdir(parents=True, exist_ok=True)
    (ROOT / 'results').mkdir(exist_ok=True)
    (ROOT / 'docs').mkdir(exist_ok=True)
    frames, coverage, missing = [], [], []
    for path in sorted((ROOT / 'data/raw').glob('PRSA_Data_*.csv')):
        df = pd.read_csv(path)
        df['timestamp'] = pd.to_datetime(df[['year','month','day','hour']]).dt.tz_localize('Asia/Shanghai')
        df = df.sort_values('timestamp').reset_index(drop=True)
        assert df.station.nunique() == 1
        station = df.station.iloc[0]
        duplicates = int(df.duplicated(['station','timestamp']).sum())
        gaps = int((df.timestamp.diff().dropna() != pd.Timedelta(hours=1)).sum())
        assert len(df) == 35064 and duplicates == gaps == 0
        assert str(df.timestamp.iloc[0]) == '2013-03-01 00:00:00+08:00'
        assert str(df.timestamp.iloc[-1]) == '2017-02-28 23:00:00+08:00'
        missing_mask = df['PM2.5'].isna()
        groups = missing_mask.ne(missing_mask.shift()).cumsum()
        max_gap = int(missing_mask.groupby(groups).sum().max())
        coverage.append(dict(station=station, rows=len(df), observed_pm25=int(df['PM2.5'].count()),
            pm25_missing_pct=missing_mask.mean()*100, longest_pm25_gap_hours=max_gap,
            duplicate_keys=duplicates, hourly_discontinuities=gaps,
            first=str(df.timestamp.iloc[0]), last=str(df.timestamp.iloc[-1]),
            pm25_min=df['PM2.5'].min(), pm25_median=df['PM2.5'].median(),
            pm25_p90=df['PM2.5'].quantile(.9), pm25_p99=df['PM2.5'].quantile(.99),
            pm25_max=df['PM2.5'].max()))
        for col in VARIABLES:
            missing.append(dict(station=station, variable=col, count=int(df[col].isna().sum()),
                                fraction=float(df[col].isna().mean())))
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)
    assert len(frames) == 12 and len(full) == 420768
    full.to_parquet(out / 'beijing.parquet', index=False)
    cov, miss = pd.DataFrame(coverage), pd.DataFrame(missing)
    cov.to_csv(ROOT / 'results/coverage.csv', index=False)
    miss.to_csv(ROOT / 'results/missingness.csv', index=False)
    pin = json.loads((ROOT / 'data/manifest.json').read_text())
    summary = cov[['station','rows','observed_pm25','pm25_missing_pct','longest_pm25_gap_hours','pm25_median','pm25_p90','pm25_max']]
    text = f'''# Dataset\n\n[UCI original](https://archive.ics.uci.edu/dataset/501/beijing+multi+site+air+quality+data), DOI 10.24432/C5RK5G, Song Chen (2017), CC BY 4.0.\n\nRetrieved {pin['retrieved_utc']}. Download URL: {pin['source_url']}\n\nArchive SHA256: `{pin['archive_sha256']}`. All 12 extracted CSV SHA256 values are pinned in [manifest](../data/manifest.json). Acquisition verifies existing pins; no Kaggle data.\n\nVerified from files: **420,768 rows; 12 stations; 35,064 hourly rows each; 2013-03-01 00:00 through 2017-02-28 23:00**. Zero duplicate station/timestamp keys, zero missing timestamps or hourly discontinuities. The files have 18 columns, including all six pollutants and six weather variables requested. PM2.5 is in micrograms per cubic metre.\n\nTimestamps are interpreted as Beijing local civil time (Asia/Shanghai, UTC+08:00); the source has separate year/month/day/hour fields without a timezone. Parquet retains timezone-aware timestamps; time-of-day features use local time. No DST ambiguity occurs.\n\n{summary.to_markdown(index=False, floatfmt='.2f')}\n\nMissing values are preserved, never interpolated from the future. Missingness by variable and station: [CSV](../results/missingness.csv). Distribution percentiles, date coverage and gap lengths: [CSV](../results/coverage.csv). These distribution summaries are descriptive, not used to select model parameters or the high-pollution threshold.\n\nHourly continuity does not mean observations are complete. PM2.5 observed coverage is {(1-full['PM2.5'].isna().mean())*100:.2f}%. Forecast exclusions are specified in PROTOCOL.md and counted in results/origins.csv.\n'''
    (ROOT / 'docs/DATASET.md').write_text(text, encoding='utf-8')
    print(summary.to_string(index=False))
    print('All structural checks passed.')

if __name__ == '__main__':
    main()
