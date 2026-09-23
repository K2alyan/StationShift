import numpy as np
import pandas as pd
from stationshift.data import features, training_indices, origins, load, TEST_START

def test_features_cannot_see_future():
    df=load()['Aotizhongxin'].iloc[:200].copy()
    original=features(df)
    changed=df.copy()
    for c in ['PM2.5','PM10','SO2','NO2','CO','O3','TEMP','PRES','DEWP','RAIN','WSPM']:
        changed.loc[101:,c]=99999
    pd.testing.assert_frame_equal(original.iloc[:101],features(changed).iloc[:101])
    assert original.shape[1]==40

def test_training_boundaries_all_budgets_horizons():
    df=load()['Aotizhongxin']
    for b in [24,72,168,720,2160]:
        start=TEST_START-pd.Timedelta(hours=b)
        for h in [1,6,24]:
            idx=training_indices(df,h,start=start,end=TEST_START,stride=1)
            assert (df.timestamp.iloc[idx-23]>=start).all()
            assert (df.timestamp.iloc[idx+h]<TEST_START).all()
            if b==24:
                assert len(idx)==0

def test_origins_have_observed_targets_and_correct_seasonal_alignment():
    for df in load().values():
        idx, table=origins(df)
        assert len(idx)>0 and table['index'].diff().dropna().eq(25).all()
        for h in [1,6,24]:
            assert df['PM2.5'].iloc[idx+h].notna().all()
            assert df['PM2.5'].iloc[idx+h-168].notna().all()
            assert (df.timestamp.iloc[idx+h].to_numpy()-df.timestamp.iloc[idx+h-24].to_numpy()==pd.Timedelta(hours=24)).all()

def test_feature_footprint_is_only_24_hours():
    df=load()['Aotizhongxin'].iloc[:200].copy()
    a=features(df).iloc[-1]
    for c in ['PM2.5','PM10','SO2','NO2','CO','O3','TEMP','PRES','DEWP','RAIN','WSPM']:
        df.loc[:175,c]=99999
    pd.testing.assert_series_equal(a,features(df).iloc[-1])
