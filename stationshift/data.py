from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HORIZONS = [1, 6, 24]
BUDGETS = [24, 72, 168, 720, 2160]
SEED = 20260923
TRAIN_END = pd.Timestamp('2016-03-01', tz='Asia/Shanghai')
DEV_END = pd.Timestamp('2016-06-01', tz='Asia/Shanghai')
TEST_START = pd.Timestamp('2016-09-01', tz='Asia/Shanghai')
TEST_END = pd.Timestamp('2017-02-28', tz='Asia/Shanghai')

def load():
    df = pd.read_parquet(ROOT / 'data/processed/beijing.parquet')
    return {name: g.reset_index(drop=True) for name, g in df.groupby('station', sort=True)}

def features(df):
    """Only observations at or before each row; max footprint 24 hours."""
    y = df['PM2.5']
    x = {f'pm_lag_{lag}': y.shift(lag) for lag in [0,1,2,3,6,12,23]}
    for col in ['PM10','SO2','NO2','CO','O3','TEMP','PRES','DEWP','RAIN','WSPM']:
        for lag in [0,3]:
            x[f'{col}_lag_{lag}'] = df[col].shift(lag)
    compass = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']
    angle = df.wd.map({v: i*np.pi/8 for i,v in enumerate(compass)})
    x['wind_sin'], x['wind_cos'] = np.sin(angle), np.cos(angle)
    x.update(hour=df.timestamp.dt.hour, weekday=df.timestamp.dt.dayofweek, month=df.timestamp.dt.month)
    for w in [3,6,12,24]:
        x[f'mean_{w}'] = y.rolling(w).mean()
        x[f'std_{w}'] = y.rolling(w).std(ddof=0)
    return pd.DataFrame(x).astype('float32')

def training_indices(df, horizon, start=None, end=TRAIN_END, stride=3, calendar=False):
    ts, y = df.timestamp, df['PM2.5']
    mask = (ts + pd.Timedelta(hours=horizon) < end) & y.shift(-horizon).notna()
    if not calendar:
        mask &= y.rolling(24).count().eq(24)
    if start is not None:
        mask &= ts >= start + pd.Timedelta(hours=0 if calendar else 23)
    else:
        mask &= ts >= ts.iloc[0] + pd.Timedelta(hours=0 if calendar else 23)
    mask &= np.arange(len(df)) % stride == 0
    return np.flatnonzero(mask)

def origins(df):
    ts, y = df.timestamp, df['PM2.5']
    candidates = np.flatnonzero((ts >= TEST_START) & (ts < TEST_END))[::25]
    records = []
    for i in candidates:
        flags = dict(targets_observed=bool(y.iloc[i+np.array(HORIZONS)].notna().all()),
                     recent_day_complete=bool(y.iloc[i-23:i+1].notna().all()),
                     week_sources_observed=bool(y.iloc[i+np.array(HORIZONS)-168].notna().all()))
        for b in BUDGETS[1:]:
            flags[f'coverage_{b}'] = bool(y.iloc[i-b+1:i+1].notna().mean() >= .9)
        records.append(dict(station=df.station.iloc[0], index=int(i), origin=ts.iloc[i],
                            eligible=all(flags.values()), **flags))
    table = pd.DataFrame(records)
    return table.loc[table.eligible, 'index'].to_numpy(), table

def freeze(data):
    """Pin scoring constants and protocol BEFORE any inference; fail on drift."""
    dev = {s: d[(d.timestamp >= TRAIN_END) & (d.timestamp < DEV_END)] for s,d in data.items()}
    high = float(pd.concat([d['PM2.5'] for d in dev.values()]).quantile(.9))
    scales = {s: float((d['PM2.5']-d['PM2.5'].shift(24)).abs().mean()) for s,d in dev.items()}
    protocol_hash = hashlib.sha256((ROOT/'docs/PROTOCOL.md').read_bytes()).hexdigest()
    amendment_hash = hashlib.sha256((ROOT/'docs/PROTOCOL_AMENDMENT.md').read_bytes()).hexdigest()
    frozen = dict(protocol_sha256=protocol_hash, amendment_sha256=amendment_hash, high_pm_threshold=high, mase_scales=scales, seed=SEED)
    path = ROOT / 'results/frozen.json'
    if path.exists():
        assert json.loads(path.read_text()) == frozen, 'Protocol/scoring constants changed after freeze'
    else:
        path.write_text(json.dumps(frozen, indent=2)+'\n')
    return frozen
