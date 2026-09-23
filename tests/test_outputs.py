"""Acceptance checks against actual measured artifacts (not mock forecasts)."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from stationshift.data import ROOT, load, features, TEST_START, training_indices
from stationshift.report import aggregate
from lightgbm import Booster

def test_every_setting_uses_identical_measured_targets():
    p=pd.read_parquet(ROOT/'results/predictions.parquet')
    assert p.station.nunique()==12
    assert not p.duplicated(['station','origin','model','history_hours','horizon']).any()
    for (_,h),g in p.groupby(['station','horizon']):
        ref=g[(g.model=='Persistence')&(g.history_hours==24)].set_index('origin').observed.sort_index()
        for _,setting in g.groupby(['model','history_hours']):
            pd.testing.assert_series_equal(setting.set_index('origin').observed.sort_index(),ref)
    quant=p[p.model=='Chronos-2']
    assert (quant.q10<=quant.q50).all() and (quant.q50<=quant.q90).all()
    assert np.array_equal(quant.prediction,quant.q50)

def test_saved_metrics_reproduce_from_predictions():
    p=pd.read_parquet(ROOT/'results/predictions.parquet')
    actual=aggregate(p,['model','history_hours','horizon'])
    saved=pd.read_csv(ROOT/'results/metrics.csv')
    for col in ['mae','rmse','mase','bias','high_mae','high_bias']:
        np.testing.assert_allclose(actual[col],saved[col],rtol=1e-12)

def test_local_tree_saved_model_matches_forecast():
    path=ROOT/'results/stations/Aotizhongxin/local_2160_h24.txt'
    if not path.exists():
        pytest.skip('Run the benchmark to regenerate locally saved, git-ignored boosters')
    df=load()['Aotizhongxin']; x=features(df)
    p=pd.read_parquet(ROOT/'results/stations/Aotizhongxin/predictions.parquet')
    rows=p[(p.model=='LightGBM global+local')&(p.history_hours==2160)&(p.horizon==24)]
    lookup={str(t):i for i,t in enumerate(df.timestamp)}
    idx=[lookup[t] for t in rows.origin]
    model=Booster(model_file=str(path))
    np.testing.assert_allclose(model.predict(x.iloc[idx]),rows.prediction,rtol=1e-12)

def test_site_contains_exact_series_and_no_fabricated_zero_context():
    site=json.loads((ROOT/'site/data.json').read_text())
    assert site['totalOrigins']==1596 and len(site['stations'])==12
    for key,g in site['series'].items():
        station,model,budget,h=key.split('|')
        if budget=='0':
            assert model=='LightGBM calendar'
        assert len(g['rows'])>0
        assert abs(np.mean([abs(r[1]-r[2]) for r in g['rows']])-g['mae'])<.0001
