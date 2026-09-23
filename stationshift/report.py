"""Aggregate saved predictions, create figures and measured milestone reports."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .data import ROOT, SEED, load

KEYS=['model','history_hours','horizon']
LABELS={0:'0h',24:'1d',72:'3d',168:'7d',720:'30d',2160:'90d'}

def score(g):
    e=g.prediction-g.observed
    high=g.high_pm
    out=dict(n=len(g),mae=e.abs().mean(),rmse=np.sqrt((e**2).mean()),mase=(e.abs()/g.mase_scale).mean(),
             bias=e.mean(),high_n=int(high.sum()),high_mae=e[high].abs().mean(),high_bias=e[high].mean())
    if 'q10' in g and g.q10.notna().all():
        for name,mask in [('overall',np.ones(len(g),dtype=bool)),('high',high.to_numpy())]:
            gg=g.loc[mask]
            residual=gg.observed.to_numpy()[:,None]-gg[['q10','q50','q90']].to_numpy()
            q=np.array([.1,.5,.9])
            out[f'{name}_pinball']=np.maximum(q*residual,(q-1)*residual).mean() if len(gg) else np.nan
            out[f'{name}_coverage80']=((gg.observed>=gg.q10)&(gg.observed<=gg.q90)).mean()
            out[f'{name}_width80']=(gg.q90-gg.q10).mean()
    return out

def aggregate(p,keys):
    rows=[]
    for key,g in p.groupby(keys,sort=True):
        rows.append(dict(zip(keys,key if isinstance(key,tuple) else (key,)),**score(g)))
    return pd.DataFrame(rows)

def thresholds(metrics,keys):
    out=[]
    for key,g in metrics.groupby(keys):
        g=g.sort_values('history_hours')
        if not (g.history_hours==2160).any():
            continue
        limit=1.1*g.loc[g.history_hours==2160,'mae'].iloc[0]
        qualifying=[int(b) for b in g.history_hours if (g.loc[g.history_hours>=b,'mae']<=limit).all()]
        out.append(dict(zip(keys,key if isinstance(key,tuple) else (key,)),threshold_hours=min(qualifying),mature_mae=float(limit/1.1)))
    return pd.DataFrame(out)

def confidence(p):
    stations=sorted(p.station.unique())
    rng=np.random.default_rng(SEED)
    samples=rng.integers(0,len(stations),(2000,len(stations)))
    base=p[(p.model=='Persistence')&(p.history_hours==24)][['station','origin','horizon','prediction']].rename(columns={'prediction':'base'})
    joined=p.merge(base,on=['station','origin','horizon'],validate='many_to_one')
    rows=[]
    for key,g in joined.groupby(KEYS):
        stats=[]
        for station in stations:
            a=g[g.station==station]
            ae=(a.prediction-a.observed).abs()
            diff=ae-(a.base-a.observed).abs()
            stats.append([ae.sum(),len(a),diff.sum()])
        v=np.array(stats)
        boot=v[samples].sum(axis=1)
        lo,hi=np.quantile(boot[:,0]/boot[:,1],[.025,.975])
        dlo,dhi=np.quantile(boot[:,2]/boot[:,1],[.025,.975])
        rows.append(dict(zip(KEYS,key),mae_ci_low=lo,mae_ci_high=hi,
            delta_vs_persistence=v[:,2].sum()/v[:,1].sum(),delta_ci_low=dlo,delta_ci_high=dhi))
    return pd.DataFrame(rows)

def curve(metrics,folder,name):
    fig,axes=plt.subplots(1,3,figsize=(14,4.2),sharey=True)
    for h,ax in zip([1,6,24],axes):
        for model,g in metrics[metrics.horizon==h].groupby('model'):
            g=g.sort_values('history_hours')
            ax.plot([list(LABELS).index(b) for b in g.history_hours],g.mae,marker='o',label=model,linewidth=1.5,markersize=4)
        ax.set_xticks(range(6),list(LABELS.values())); ax.set_title(f'+{h} hour'); ax.grid(alpha=.2)
        ax.set_xlabel('Allowed local history window')
    axes[0].set_ylabel('PM2.5 MAE (µg/m³)')
    axes[-1].legend(fontsize=7,loc='upper left',bbox_to_anchor=(1,1))
    fig.tight_layout(); fig.savefig(folder/f'{name}.png',dpi=160,bbox_inches='tight'); plt.close(fig)

def station_distribution(metrics,folder):
    mature=metrics[metrics.history_hours==2160]
    models=sorted(mature.model.unique())
    fig,axes=plt.subplots(1,3,figsize=(14,5),sharey=True)
    for h,ax in zip([1,6,24],axes):
        for j,m in enumerate(models):
            values=mature[(mature.model==m)&(mature.horizon==h)].mae.to_numpy()
            ax.scatter(np.full(len(values),j),values,alpha=.65,s=24)
            ax.plot([j-.2,j+.2],[np.median(values)]*2,color='black')
        ax.set_xticks(range(len(models)),models,rotation=65,ha='right',fontsize=8)
        ax.set_title(f'+{h} hour, 90d budget'); ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Per-station MAE (µg/m³)')
    fig.tight_layout(); fig.savefig(folder/'station_distribution.png',dpi=160); plt.close(fig)

def table(metrics,costs):
    t=metrics.pivot(index=['model','history_hours'],columns='horizon',values='mae').rename(columns={1:'H1 MAE',6:'H6 MAE',24:'H24 MAE'})
    high=metrics.assign(total=lambda d:d.high_mae*d.high_n).groupby(['model','history_hours'])[['total','high_n']].sum()
    t['High-PM MAE']=high.total/high.high_n
    runtime=costs.groupby(['model','history_hours'])[['train_seconds','inference_seconds']].sum()
    t['Fit sec']=runtime.train_seconds; t['Infer sec']=runtime.inference_seconds
    t=t.reset_index().rename(columns={'model':'Model','history_hours':'History h'})
    return t.to_markdown(index=False,floatfmt='.2f')

def errors(p):
    data=load(); rows=[]
    mature=p[p.history_hours==2160].copy()
    mature['ae']=(mature.prediction-mature.observed).abs()
    for model,g in mature.groupby('model'):
        for r in g.nlargest(20,'ae').itertuples():
            d=data[r.station]; i=int(d.index[d.timestamp==pd.Timestamp(r.origin)][0]); end=i+r.horizon
            change=d['PM2.5'].iloc[end]-d['PM2.5'].iloc[end-24]
            tags=[]
            if change>50: tags.append('rapid rise')
            if change< -50: tags.append('rapid fall')
            if r.high_pm: tags.append('high episode')
            if pd.notna(d.wd.iloc[end]) and pd.notna(d.wd.iloc[i]) and d.wd.iloc[end]!=d.wd.iloc[i]: tags.append('wind direction change')
            if abs(d.TEMP.iloc[end]-d.TEMP.iloc[i])>5 or abs(d.PRES.iloc[end]-d.PRES.iloc[i])>5: tags.append('weather transition')
            mask=d['PM2.5'].iloc[max(0,i-2159):i+1].isna()
            longest=int(mask.groupby(mask.ne(mask.shift()).cumsum()).sum().max())
            if longest>=24: tags.append('historical gap >=24h')
            if abs(r.prediction-d['PM2.5'].iloc[i])<abs(r.prediction-r.observed): tags.append('lag-like forecast')
            rows.append(dict(model=model,station=r.station,origin=r.origin,horizon=r.horizon,observed=r.observed,
                prediction=r.prediction,error=r.prediction-r.observed,change_24h=change,tags='; '.join(tags)))
    return pd.DataFrame(rows)

def main():
    folder=ROOT/'results'; figs=folder/'figures'; figs.mkdir(exist_ok=True)
    complete=sorted((folder/'stations').glob('*/complete.json'))
    assert complete
    frozen=json.loads((folder/'frozen.json').read_text())
    for f in complete:
        done=json.loads(f.read_text())
        assert all(done[k]==frozen[k] for k in ['protocol_sha256','amendment_sha256'])
    p=pd.concat([pd.read_parquet(f.parent/'predictions.parquet') for f in complete],ignore_index=True)
    costs=pd.concat([pd.read_csv(f.parent/'costs.csv') for f in complete],ignore_index=True)
    cohort=pd.concat([pd.read_csv(f.parent/'origins.csv') for f in complete],ignore_index=True)
    assert not p.duplicated(['station','origin',*KEYS]).any()
    expected=cohort[cohort.eligible].groupby('station').size()
    assert p.groupby(['station',*KEYS]).size().eq(p.groupby(['station',*KEYS]).size().index.get_level_values('station').map(expected)).all()
    pooled=aggregate(p,KEYS); station=aggregate(p,['station',*KEYS])
    if len(complete)>1:
        pooled=pooled.merge(confidence(p),on=KEYS)
    for frame,name in [(pooled,'metrics'),(station,'station_metrics'),(costs,'costs'),(cohort,'origins')]:
        frame.to_csv(folder/f'{name}.csv',index=False)
    p.to_parquet(folder/'predictions.parquet',index=False)
    th=thresholds(pooled,['model','horizon']); th.to_csv(folder/'history_threshold.csv',index=False)
    thresholds(station,['station','model','horizon']).to_csv(folder/'station_history_threshold.csv',index=False)
    curve(pooled,figs,'adaptation_pooled')
    for s,g in station.groupby('station'):
        curve(g,figs,f'adaptation_{s}')
    probabilistic=pooled[pooled.model=='Chronos-2'][['history_hours','horizon','overall_pinball','overall_coverage80','overall_width80','high_pinball','high_coverage80','high_width80']]
    probabilistic.to_csv(folder/'probabilistic.csv',index=False)
    errs=errors(p); errs.to_csv(folder/'worst_cases.csv',index=False)
    milestone=station[station.station=='Aotizhongxin']
    mc=costs[costs.station=='Aotizhongxin']
    mtext=f'''# Milestone 1 — measured\n\nUCI data downloaded, pinned and verified: 12 stations, 420,768 rows, no duplicate timestamps or hourly discontinuities. See DATASET.md and PROTOCOL.md.\n\nInitial holdout: Aotizhongxin. Test interval September 2016–February 2017. {int(expected['Aotizhongxin'])} common forecast origins; +1/+6/+24-hour targets. Other 11 stations supply LightGBM fitting data. All results below are executed predictions, not examples. PM2.5 errors are µg/m³.\n\n{table(milestone,mc)}\n\n![Initial adaptation curves](../results/figures/adaptation_Aotizhongxin.png)\n\n0h is a separately labeled donor-trained calendar model; Chronos, persistence and seasonal forecasts require observations. Global+local has zero fitting rows at 24h and therefore equals global. Chronos remains zero-shot task adaptation at every positive context budget. Positive-budget global and short-lag baselines plateau by construction.\n\nTimes are exclusive measured fit/inference costs; reused models and predictions have zero incremental cost. Chronos produces all horizons in one call, charged to H1 in raw costs. Download, startup and features excluded. Full MAE/RMSE/MASE, per-origin predictions, cost rows and exclusion flags are in results/. No model or protocol selection follows these test results.\n'''
    (ROOT/'docs/MILESTONE_1.md').write_text(mtext,encoding='utf-8')
    if len(complete)==12:
        station_distribution(station,figs)
        hardware=json.loads((folder/'hardware.json').read_text())
        counts=cohort.groupby('station').eligible.agg(['size','sum']).rename(columns={'size':'candidates','sum':'retained'})
        text=f'''# StationShift measured results\n\nAll 12 station holdouts completed under the frozen protocol. **{len(cohort[cohort.eligible])} retained station-origin pairs** from {len(cohort)} candidates, each scored at 1, 6 and 24 hours. PM2.5 errors are µg/m³.\n\n## Accuracy and cost\n\n{table(pooled,costs)}\n\nHigh-PM MAE combines the three horizons, weighting qualifying targets equally. Threshold: observed PM2.5 >168 µg/m³, the development-only pooled 90th percentile. Horizon-specific high errors and bias are in metrics.csv. No health interpretation is intended.\n\n![Pooled adaptation curves](../results/figures/adaptation_pooled.png)\n\n## History to within 10% of mature performance\n\n{th.to_markdown(index=False,floatfmt='.2f')}\n\nEarliest budget with all larger supported budgets also within 10% of its own 90d MAE; not a cross-model usefulness threshold. Per-station thresholds are in station_history_threshold.csv.\n\n## Probabilistic performance (Chronos only)\n\n{probabilistic.to_markdown(index=False,floatfmt='.3f')}\n\nIntervals target 80% coverage. Pinball averages quantiles .1/.5/.9. High-event calibration is conditional on observed extremes, so it need not equal marginal 80% even for a marginally calibrated forecaster. Deterministic baselines have no comparable intervals.\n\n## Coverage and uncertainty\n\n{counts.to_markdown()}\n\nStation-level MAE/RMSE/MASE and bias: station_metrics.csv; individual station curves: results/figures/adaptation_STATION.png. metrics.csv contains 95% paired station-cluster bootstrap intervals and paired MAE differences against persistence (2000 replicates). Resampling whole stations preserves serial dependence. Correlated citywide shocks and only 12 stations limit interval interpretation. Complete-history eligibility and sparse 25-hour sampling limit generalization to outages or every hourly issuance.\n\n## Efficiency\n\nGPU: {hardware['gpu']}; CPU: {hardware['processor']}; four CPU threads. Chronos has {hardware['pretrained_parameters']:,} frozen parameters. No API fees. costs.csv reports actual donor/local sample counts, tree leaf counts and exclusive fit/inference times. Cumulative process peak CUDA allocation at station completion is in each complete.json; these are not independent station peaks. Model load timing and package versions: hardware.json. Local fitting samples can be fewer than the nominal clock-hour budget due to horizon/feature boundaries and missingness. Tree leaf counts are not directly comparable to neural parameter counts.\n\n## Interpretation and limitations\n\nThe experiment compares **history-window budgets**, not the time required after a single sensor deployment. LightGBM global+local uses a frozen pre-test H-hour fitting window and rolling 24-hour inference context; Chronos uses a rolling H-hour context with no fitting. Thus the models consume different kinds of history and do not have equal total acquisition budgets. A plateau in the global/naive curves reflects their fixed feature footprints. H=0 has only the donor-trained calendar reference; a context-free Chronos forecast is N/A.\n\nThese are zero-shot task-adaptation measurements, not a guarantee Beijing was absent from pretraining. No claim of novelty for air-quality forecasting, station holdout, uncertainty, or chronological evaluation. Only one TSFM and one fixed LightGBM specification were tested. There is no test tuning or optional masking study.\n\n## Error inspection\n\nTop 20 absolute errors for each mature model: worst_cases.csv. Tags are overlapping observed-variable descriptions (rapid rises/falls, high targets, wind changes, weather changes, long historical gaps, lag-like predictions). They do not establish atmospheric causation. Negative bias means underprediction. The report's companion FINDINGS.md summarizes measured comparisons and these cases.\n'''
        (ROOT/'docs/RESULTS.md').write_text(text,encoding='utf-8')
        cis=pooled[(pooled.history_hours==2160)&pooled.model.isin(['Chronos-2','LightGBM global','LightGBM global+local','Persistence'])][['model','horizon','mae','mae_ci_low','mae_ci_high','delta_vs_persistence','delta_ci_low','delta_ci_high']]
        crossings=sum(json.loads(f.read_text())['quantile_crossings'] for f in complete)
        with (ROOT/'docs/RESULTS.md').open('a',encoding='utf-8') as stream:
            stream.write('\n## Mature-budget confidence intervals\n\n'+cis.to_markdown(index=False,floatfmt='.2f'))
            stream.write('\n\nNegative paired delta favors the named model over persistence.\n\n![Station distributions](../results/figures/station_distribution.png)\n')
            stream.write(f'\nQuantile ordering: {crossings} of {len(cohort[cohort.eligible])*5*24:,} generated trajectory steps required endpoint correction. The median was preserved; see [amendment](PROTOCOL_AMENDMENT.md). All reported intervals and pinball scores use corrected endpoints.\n')
    print(table(pooled,costs))

if __name__=='__main__':
    main()
