"""Export only completed measured results into a small offline static explorer."""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
assert (ROOT/'docs/RESULTS.md').exists(), 'Final results must exist before building the explorer'
p=pd.read_parquet(ROOT/'results/predictions.parquet')
assert p.station.nunique()==12
series={}
for (station,model,budget,horizon),g in p.groupby(['station','model','history_hours','horizon']):
    g=g.sort_values('origin')
    rows=[]
    for r in g.itertuples():
        when=pd.Timestamp(r.origin)+pd.Timedelta(hours=int(horizon))
        q10=getattr(r,'q10',float('nan')); q90=getattr(r,'q90',float('nan'))
        rows.append([int(when.timestamp()*1000),round(r.observed,4),round(r.prediction,4),
            round(q10,4) if pd.notna(q10) else None,round(q90,4) if pd.notna(q90) else None])
    e=g.prediction-g.observed
    series[f'{station}|{model}|{budget}|{horizon}']={
        'rows':rows,'mae':float(e.abs().mean()),'rmse':float((e.pow(2).mean())**.5),
        'bias':float(e.mean()),'highMaE':float(e[g.high_pm].abs().mean()),
        'coverage':float(((g.observed>=g.q10)&(g.observed<=g.q90)).mean()) if model=='Chronos-2' else None}
payload={'stations':sorted(p.station.unique()),'models':sorted(p.model.unique()),'series':series,
         'totalOrigins':int(p[['station','origin']].drop_duplicates().shape[0]),'threshold':168}
site=ROOT/'site'; site.mkdir(exist_ok=True)
(site/'data.json').write_text(json.dumps(payload,separators=(',',':'),allow_nan=False),encoding='utf-8')
print('Exported',len(series),'measured series,',round((site/'data.json').stat().st_size/1e6,2),'MB')
