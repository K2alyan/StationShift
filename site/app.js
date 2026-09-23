'use strict';
const $=id=>document.getElementById(id);
const controls=['station','horizon','history','model'];
let data, current;
const fmt=n=>n==null?'—':n.toFixed(2);
const dateFmt=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Shanghai',year:'numeric',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
function populate(id,values,selected){for(const v of values){const o=document.createElement('option');o.value=v;o.textContent=v;$(id).append(o);}$(id).value=selected;}
function svgEl(name,attrs,text){const e=document.createElementNS('http://www.w3.org/2000/svg',name);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,String(v));if(text!=null)e.textContent=text;return e;}
function chart(rows,probabilistic){
 const svg=$('chart');for(const e of [...svg.children])if(!['title','desc'].includes(e.tagName))e.remove();
 const left=55,top=20,w=920,h=265;
 const minT=rows[0][0],maxT=rows[rows.length-1][0];
 const low=Math.min(0,...rows.flatMap(r=>[r[1],r[2],r[3]??0]));
 const high=Math.max(...rows.flatMap(r=>[r[1],r[2],r[4]??0]))*1.08;
 const x=t=>left+(t-minT)/(maxT-minT||1)*w,y=v=>top+h-(v-low)/(high-low||1)*h;
 for(let j=0;j<5;j++){const value=low+(high-low)*j/4,yy=y(value);svg.append(svgEl('line',{x1:left,y1:yy,x2:left+w,y2:yy,stroke:'#e3e9df'}));svg.append(svgEl('text',{x:left-9,y:yy+4,'text-anchor':'end',fill:'#536b64','font-size':11},Math.round(value)));}
 const path=col=>rows.map((r,i)=>(i?'L':'M')+x(r[0]).toFixed(1)+','+y(r[col]).toFixed(1)).join(' ');
 if(probabilistic){const d=path(3)+' '+[...rows].reverse().map(r=>'L'+x(r[0]).toFixed(1)+','+y(r[4]).toFixed(1)).join(' ')+' Z';svg.append(svgEl('path',{d,fill:'#edcaae','fill-opacity':.4}));}
 for(const [col,color]of [[1,'#142d2a'],[2,'#b75b2b']])svg.append(svgEl('path',{d:path(col),fill:'none',stroke:color,'stroke-width':1.5}));
 for(let j=0;j<6;j++){const t=minT+(maxT-minT)*j/5;svg.append(svgEl('text',{x:x(t),y:top+h+25,'text-anchor':j===0?'start':j===5?'end':'middle',fill:'#536b64','font-size':11},new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Shanghai',month:'short',day:'numeric'}).format(t)));}
 svg.append(svgEl('text',{x:left,y:12,fill:'#536b64','font-size':10},'PM2.5 · µg/m³'));
 $('chart-title').textContent=`${$('station').value}: observed PM2.5 and ${$('model').value} forecasts`;
}
function update(){
 const station=$('station').value,model=$('model').value,budget=Number($('history').value),h=$('horizon').value;
 current=data.series[`${station}|${model}|${budget}|${h}`];
 $('result').hidden=!current;
 if(!current){$('status').textContent=budget===0?'No forecast: this model requires local observations. Choose LightGBM calendar for the 0-hour reference.':model==='LightGBM calendar'?'The calendar-only reference is defined only at 0 hours.':'No forecast: the weekly seasonal baseline requires at least 7 days of history.';return;}
 $('status').textContent=`${current.rows.length} eligible origins · same targets for every supported model and budget`;
 $('mae').textContent=fmt(current.mae);$('rmse').textContent=fmt(current.rmse);$('high').textContent=fmt(current.highMaE);
 $('coverage').textContent=current.coverage==null?'Not available':(100*current.coverage).toFixed(1)+'%';
 $('interval-legend').hidden=current.coverage==null;
 chart(current.rows,current.coverage!=null);
 const explanations={
 'Chronos-2':`${budget} hours of rolling PM2.5 context; no local fitting. Median forecast and corrected 10%–90% quantiles from the pinned Chronos-2 checkpoint.`,
 'LightGBM global':'Donor-trained on the other 11 stations, with 24 hours of local inference features. No target-station labels used for fitting.',
 'LightGBM global+local':`${budget} hours allowed in a frozen pre-test local fitting window, plus donor data and rolling 24-hour inference features.${budget===24?' No usable local training examples fit inside this 1-day window, so this equals the global model.':''}`,
 'LightGBM calendar':'0 local readings: a donor-trained calendar-only reference. It uses origin hour, weekday and month.',
 'Persistence':'Latest observed PM2.5 carried forward. No model fitting; extra context does not change its forecast.',
 'Seasonal day':'Same target hour one day earlier. No fitting; at +24h this equals persistence.',
 'Seasonal week':'Same target hour one week earlier. No model fitting.'};
 $('regime').textContent=explanations[model];
 $('rows').replaceChildren();
 for(const r of current.rows){const tr=document.createElement('tr');for(const text of [dateFmt.format(r[0]),...r.slice(1).map(fmt)]){const td=document.createElement('td');td.textContent=text;tr.append(td);}$('rows').append(tr);}
}
$('download').addEventListener('click',()=>{if(!current)return;const csv='target_time_utc,observed,prediction,q10,q90\n'+current.rows.map(r=>[new Date(r[0]).toISOString(),...r.slice(1).map(v=>v??'')].join(',')).join('\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));const a=document.createElement('a');a.href=url;a.download=`coldstartaq-${$('station').value}-${$('horizon').value}h.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
fetch('data.json').then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}).then(d=>{data=d;populate('station',d.stations,'Aotizhongxin');populate('model',d.models,'Chronos-2');$('total').textContent=d.totalOrigins.toLocaleString();for(const id of controls)$(id).addEventListener('change',update);update();}).catch(e=>{$('status').textContent='Could not load saved results. Serve the site with the README command and reload. '+e.message;});
