"""Run: python -m stationshift.benchmark --station Aotizhongxin (or --all)."""
import argparse
import json
import platform
import time
from importlib.metadata import version
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from .data import ROOT, BUDGETS, HORIZONS, SEED, TEST_START, load, features, training_indices, origins, freeze

CALENDAR = ['hour', 'weekday', 'month']

def fit_model(x, y, weights=None):
    model = LGBMRegressor(n_estimators=200, learning_rate=.05, num_leaves=31,
        min_child_samples=50, max_bin=63, reg_lambda=1, n_jobs=4,
        random_state=SEED, deterministic=True, force_col_wise=True, verbosity=-1)
    t = time.perf_counter()
    model.fit(x, y, sample_weight=weights)
    elapsed = time.perf_counter()-t
    leaves = sum(t['num_leaves'] for t in model.booster_.dump_model()['tree_info'])
    return model, elapsed, leaves

def run_station(station, data, xs, frozen, pipeline):
    import torch
    folder = ROOT / 'results/stations' / station
    folder.mkdir(parents=True, exist_ok=True)
    if (folder/'complete.json').exists():
        prior=json.loads((folder/'complete.json').read_text())
        assert prior['protocol_sha256'] == frozen['protocol_sha256'] and prior['amendment_sha256'] == frozen['amendment_sha256']
        print('Already complete:', station, flush=True)
        return
    df, x = data[station], xs[station]
    ii, cohort = origins(df)
    cohort.to_csv(folder/'origins.csv', index=False)
    assert len(ii) > 0
    y = df['PM2.5'].to_numpy()
    predictions, costs = [], []
    quantile_crossings = 0
    def add(model, b, h, pred, q=None):
        for k, i in enumerate(ii):
            row = dict(station=station, origin=str(df.timestamp.iloc[i]), horizon=h,
                model=model, history_hours=b, observed=float(y[i+h]), prediction=float(pred[k]),
                high_pm=bool(y[i+h]>frozen['high_pm_threshold']), mase_scale=frozen['mase_scales'][station])
            if q is not None:
                row.update(q10=float(q[k,0]), q50=float(q[k,1]), q90=float(q[k,2]))
            predictions.append(row)
    def cost(model, b, h, train, infer, nlocal=0, ndonor=0, leaves=0, reused=False):
        costs.append(dict(station=station, model=model, history_hours=b, horizon=h,
            train_seconds=train, inference_seconds=infer, local_fit_samples=nlocal,
            donor_fit_samples=ndonor, fitted_leaves=leaves, reused=reused,
            n_origins=len(ii), device='cuda' if model=='Chronos-2' else 'cpu'))

    for h in HORIZONS:
        for model, lag, minb in [('Persistence',h,24),('Seasonal day',24,24),('Seasonal week',168,168)]:
            t=time.perf_counter()
            p=y[ii+h-lag]
            sec=time.perf_counter()-t
            for b in BUDGETS:
                if b>=minb:
                    add(model,b,h,p)
                    cost(model,b,h,0,sec if b==minb else 0,reused=b!=minb)
        donor_x, donor_y, cal_x, cal_y = [], [], [], []
        for name,d in data.items():
            if name==station:
                continue
            idx=training_indices(d,h)
            donor_x.append(xs[name].iloc[idx]); donor_y.append(d['PM2.5'].iloc[idx+h].to_numpy())
            idx=training_indices(d,h,calendar=True)
            cal_x.append(xs[name].iloc[idx][CALENDAR]); cal_y.append(d['PM2.5'].iloc[idx+h].to_numpy())
        dx,dy = pd.concat(donor_x,ignore_index=True), np.concatenate(donor_y)
        model,sec,leaves=fit_model(pd.concat(cal_x,ignore_index=True),np.concatenate(cal_y))
        t=time.perf_counter(); p=model.predict(x.iloc[ii][CALENDAR]); infer=time.perf_counter()-t
        add('LightGBM calendar',0,h,p)
        cost('LightGBM calendar',0,h,sec,infer,ndonor=sum(map(len,cal_y)),leaves=leaves)
        model.booster_.save_model(str(folder/f'calendar_h{h}.txt'))
        model,sec,leaves=fit_model(dx,dy)
        model.booster_.save_model(str(folder/f'global_h{h}.txt'))
        t=time.perf_counter(); p=model.predict(x.iloc[ii]); infer=time.perf_counter()-t
        for b in BUDGETS:
            add('LightGBM global',b,h,p)
            cost('LightGBM global',b,h,sec if b==24 else 0,infer if b==24 else 0,
                 ndonor=len(dy),leaves=leaves,reused=b!=24)
            local_idx=training_indices(df,h,start=TEST_START-pd.Timedelta(hours=b),end=TEST_START,stride=1)
            if len(local_idx):
                xx=pd.concat([dx,x.iloc[local_idx]],ignore_index=True)
                yy=np.concatenate([dy,y[local_idx+h]])
                weights=np.r_[np.ones(len(dy)),np.full(len(local_idx),len(dy)/11/len(local_idx))]
                fitted,ts,leaf=fit_model(xx,yy,weights)
                fitted.booster_.save_model(str(folder/f'local_{b}_h{h}.txt'))
                t=time.perf_counter(); pp=fitted.predict(x.iloc[ii]); ins=time.perf_counter()-t
            else:
                pp,ts,ins,leaf=p,0,0,leaves
            add('LightGBM global+local',b,h,pp)
            cost('LightGBM global+local',b,h,ts,ins,len(local_idx),len(dy),leaf,reused=not len(local_idx))
        print(station,'LightGBM horizon',h,'done',flush=True)

    for b in BUDGETS:
        contexts=np.stack([y[i-b+1:i+1] for i in ii]).astype('float32')
        torch.cuda.synchronize(); t=time.perf_counter()
        with torch.inference_mode():
            quantiles,_=pipeline.predict_quantiles(contexts[:,None,:],prediction_length=24,
                quantile_levels=[.1,.5,.9],batch_size=16,context_length=b,cross_learning=False)
        torch.cuda.synchronize(); sec=time.perf_counter()-t
        # API returns one [target, prediction, quantile] tensor per independent series.
        q=np.stack([a.detach().cpu().numpy().reshape(24,3) for a in quantiles])
        assert np.isfinite(q).all()
        quantile_crossings += int(((q[:,:,0]>q[:,:,1]) | (q[:,:,1]>q[:,:,2])).sum())
        q[:,:,0] = np.minimum(q[:,:,0],q[:,:,1])
        q[:,:,2] = np.maximum(q[:,:,2],q[:,:,1])
        for h in HORIZONS:
            add('Chronos-2',b,h,q[:,h-1,1],q[:,h-1,:])
            cost('Chronos-2',b,h,0,sec if h==1 else 0,reused=h!=1)
        print(station,'Chronos context',b,'seconds',round(sec,2),flush=True)
    pd.DataFrame(predictions).to_parquet(folder/'predictions.parquet',index=False)
    pd.DataFrame(costs).to_csv(folder/'costs.csv',index=False)
    (folder/'complete.json').write_text(json.dumps(dict(protocol_sha256=frozen['protocol_sha256'],amendment_sha256=frozen['amendment_sha256'],
         origins=len(ii),quantile_crossings=quantile_crossings,
         cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated()),indent=2))
    print('COMPLETE',station,len(ii),'origins',flush=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--station',default='Aotizhongxin'); p.add_argument('--all',action='store_true')
    args=p.parse_args()
    data=load(); frozen=freeze(data); xs={s:features(d) for s,d in data.items()}
    from chronos import Chronos2Pipeline
    import torch
    torch.manual_seed(SEED); torch.set_num_threads(4)
    assert torch.cuda.is_available(), 'Protocol specifies CUDA; use an explicit protocol amendment for CPU'
    t=time.perf_counter()
    pipeline=Chronos2Pipeline.from_pretrained(str(ROOT/'models/chronos-2'),device_map='cuda',torch_dtype=torch.float32,local_files_only=True)
    pipeline.model.eval()
    hardware=dict(platform=platform.platform(),processor=platform.processor(),gpu=torch.cuda.get_device_name(),
        torch_cuda=torch.version.cuda,threads=4,model_load_seconds=time.perf_counter()-t,
        pretrained_parameters=sum(a.numel() for a in pipeline.model.parameters()),
        packages={m:version(m) for m in ['chronos-forecasting','torch','transformers','numpy','pandas','lightgbm','pyarrow','matplotlib']})
    (ROOT/'results/hardware.json').write_text(json.dumps(hardware,indent=2))
    for station in (list(data) if args.all else [args.station]):
        run_station(station,data,xs,frozen,pipeline)

if __name__=='__main__':
    main()
