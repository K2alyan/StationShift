import numpy as np
import pandas as pd
from stationshift.report import score, thresholds, confidence

def test_metrics_with_hand_computed_forecasts():
    g=pd.DataFrame(dict(observed=[0.,10.],prediction=[2.,6.],mase_scale=[2.,2.],high_pm=[False,True],
                        q10=[-1.,5.],q50=[2.,6.],q90=[3.,9.]))
    s=score(g)
    assert s['mae']==3 and s['rmse']==np.sqrt(10) and s['mase']==1.5
    assert s['bias']==-1 and s['high_mae']==4 and s['high_bias']==-4
    assert s['overall_coverage80']==.5 and s['high_coverage80']==0 and s['overall_width80']==4
    assert np.isclose(s['overall_pinball'],(0.1+1+0.3+0.5+2+0.9)/6)

def test_threshold_requires_sustained_performance():
    g=pd.DataFrame(dict(model=['test']*5,horizon=[24]*5,history_hours=[24,72,168,720,2160],mae=[10.,12.,11.,10.,10.]))
    assert thresholds(g,['model','horizon']).threshold_hours.iloc[0]==168

def test_paired_bootstrap_identical_models_have_zero_delta():
    rows=[]
    for station in ['a','b','c']:
        for model in ['Persistence','candidate']:
            for i in range(3):
                rows.append(dict(station=station,origin=str(i),model=model,history_hours=24,horizon=1,observed=float(i),prediction=2.))
    ci=confidence(pd.DataFrame(rows))
    assert (ci[['delta_vs_persistence','delta_ci_low','delta_ci_high']]==0).all().all()
