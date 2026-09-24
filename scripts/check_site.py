"""Standalone headless fallback when the in-app browser is unavailable."""
from pathlib import Path
import json
from itertools import product
from decimal import Decimal, ROUND_HALF_UP
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
def fixed(value,places):
    # Match browser toFixed at exact half ties (Python format uses half-even).
    return str(Decimal.from_float(value).quantize(Decimal(10)**-places,rounding=ROUND_HALF_UP))

out=ROOT/'results/browser'; out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
    errors=[]; bad_responses=[]
    page.on('pageerror',lambda err: errors.append(str(err)))
    page.on('response',lambda r: bad_responses.append(f'{r.status} {r.url}') if r.status>=400 else None)
    page.goto('http://127.0.0.1:8000/',wait_until='networkidle')
    page.locator('#result').wait_for(state='visible')
    assert page.title()=='StationShift: Time-Series Foundation Models Under New-Station Distribution Shift'
    assert page.locator('h1').inner_text()=='StationShift'
    assert page.locator('.site-header .brand').inner_text()=='StationShift'
    assert page.locator('meta[name="description"]').get_attribute('content')=='When do time-series foundation models transfer to a new environmental monitoring station?'
    assert page.locator('#mae').inner_text()=='55.94'
    assert page.locator('#station option').count()==12
    data=json.loads((ROOT/'site/data.json').read_text())
    for width in [1440,1024,768,390]:
        page.set_viewport_size({'width':width,'height':1100 if width>390 else 844})
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),width
        page.screenshot(path=str(out/f'editorial-{width}.png'),full_page=True)
        if width==1440:
            page.screenshot(path=str(out/'desktop.png'),full_page=True)
        if width==390:
            page.screenshot(path=str(out/'mobile.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1100})
    page.locator('#station').select_option('Wanliu')
    page.locator('#horizon').select_option('6')
    page.locator('#history').select_option('2160')
    expected=data['series']['Wanliu|Chronos-2|2160|6']
    assert page.locator('#mae').inner_text()==f"{expected['mae']:.2f}"
    assert page.locator('#rows tr').count()==len(expected['rows'])
    # Display calculations use the exact station / horizon / history reference.
    ref=data['series']['Wanliu|LightGBM global|2160|6']
    def signed(value):
        value=float(fixed(value,1))
        return ('−' if value<0 else '+' if value>0 else '')+fixed(abs(value),1)
    for field,element in [('mae','mae'),('rmse','rmse'),('highMaE','high')]:
        delta=100*(expected[field]-ref[field])/ref[field]
        assert page.locator(f'#{element}-delta').inner_text()==f'{signed(delta)}% vs global LightGBM'
    assert page.locator('#coverage-delta').inner_text()==f"{signed(expected['coverage']*100-80)} pp vs nominal"
    page.locator('#values-toggle').focus(); page.keyboard.press('Enter')
    assert page.locator('#measured-values').is_visible()
    assert page.locator('#values-toggle').get_attribute('aria-expanded')=='true'
    page.locator('#values-toggle').click()
    assert page.locator('#measured-values').is_hidden()
    page.locator('#history').select_option('0')
    assert page.locator('#result').is_hidden() and 'requires local observations' in page.locator('#status').inner_text()
    page.locator('#model').select_option('LightGBM calendar')
    assert page.locator('#result').is_visible()
    assert page.locator('#coverage').inner_text()=='Not available'
    assert page.locator('#mae-delta').is_hidden() and page.locator('#coverage-delta').is_hidden()
    page.locator('#model').select_option('Seasonal week')
    page.locator('#history').select_option('72')
    assert page.locator('#result').is_hidden() and '7 days' in page.locator('#status').inner_text()
    page.locator('#history').select_option('168')
    assert page.locator('#result').is_visible()
    with page.expect_download() as download:
        page.locator('#download').click()
    assert download.value.suggested_filename=='stationshift-Wanliu-6h.csv'
    download.value.save_as(str(out/'download.csv'))
    assert (out/'download.csv').read_text().startswith('target_time_utc,observed,prediction,q10,q90')
    page.locator('#model').select_option('LightGBM global+local')
    page.locator('#history').select_option('24')
    assert 'No usable local training examples' in page.locator('#regime').inner_text()
    page.locator('#station').focus(); page.keyboard.press('Tab')
    assert page.locator('#horizon').evaluate('(e)=>e===document.activeElement')
    page.set_viewport_size({'width':390,'height':844})
    assert page.locator('h1').inner_text()=='StationShift'
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    assert page.locator('.chart-wrap').evaluate('(e)=>e.scrollWidth>e.clientWidth && getComputedStyle(e).overflowX==="auto"')
    page.locator('.chart-wrap').focus(); page.keyboard.press('ArrowRight')
    page.wait_for_function('document.querySelector(".chart-wrap").scrollLeft>0')
    page.emulate_media(reduced_motion='reduce')
    assert page.evaluate('getComputedStyle(document.documentElement).scrollBehavior')=='auto'
    assert page.evaluate('Array.from(document.querySelectorAll("a")).filter(a=>a.getAttribute("href")?.startsWith("#")).every(a=>document.querySelector(a.getAttribute("href")))')
    # Exhaustively exercise the real UI update path for all 1,512 selector states,
    # on both desktop and mobile. No model calls or metric artifact writes.
    cases=[]
    for station,horizon,budget,model in product(data['stations'],[1,6,24],[0,24,72,168,720,2160],data['models']):
        key=f'{station}|{model}|{budget}|{horizon}'
        g=data['series'].get(key)
        ref=data['series'].get(f'{station}|LightGBM global|{budget}|{horizon}')
        case={'station':station,'horizon':str(horizon),'history':str(budget),'model':model,'key':key,'expected':None}
        if g:
            case['expected']={'mae':fixed(g['mae'],2),'rmse':fixed(g['rmse'],2),'high':fixed(g['highMaE'],2),
                'coverage':fixed(100*g['coverage'],1)+'%' if g['coverage'] is not None else 'Not available',
                'n':len(g['rows']),'quantiles':g['coverage'] is not None,'deltas':{}}
            for field,element in [('mae','mae'),('rmse','rmse'),('highMaE','high')]:
                if ref and model!='LightGBM global' and ref[field]>0:
                    case['expected']['deltas'][element]=f"{signed(100*(g[field]-ref[field])/ref[field])}% vs global LightGBM"
            if g['coverage'] is not None:
                case['expected']['deltas']['coverage']=f"{signed(100*g['coverage']-80)} pp vs nominal"
        cases.append(case)
    for width in [1440,390]:
        page.set_viewport_size({'width':width,'height':900})
        for offset in range(0,len(cases),100):
            failures=page.evaluate('''cases => {
                const failures=[];
                for(const state of cases){
                    for(const id of ['station','horizon','history','model'])document.getElementById(id).value=state[id];
                    document.getElementById('model').dispatchEvent(new Event('change',{bubbles:true}));
                    const expected=state.expected;
                    const fail=what=>failures.push(state.key+': '+what);
                    if(document.getElementById('result').hidden!==!expected)fail('availability');
                    if(!expected)continue;
                    for(const id of ['mae','rmse','high','coverage']){
                        if(document.getElementById(id).textContent!==expected[id])fail(id);
                        const el=document.getElementById(id+'-delta'),delta=expected.deltas[id];
                        if(el.hidden!==!delta || (delta && el.textContent!==delta))fail(id+' delta');
                    }
                    if(document.querySelectorAll('#rows tr').length!==expected.n)fail('table rows');
                    if(document.querySelectorAll('[data-series="interval"]').length!==Number(expected.quantiles))fail('interval plot');
                    if(document.getElementById('interval-legend').hidden!==!expected.quantiles)fail('interval legend');
                    if(document.getElementById('forecast-legend').textContent!==state.model+' forecast')fail('model legend');
                    if(document.documentElement.scrollWidth>window.innerWidth)fail('overflow');
                }
                return failures;
            }''',cases[offset:offset+100])
            assert not failures,failures[:10]
        print(f'Passed {len(cases)} selector states at {width}px',flush=True)
    assert not errors, errors
    assert not bad_responses, bad_responses
    # Actual failed-resource path also gives a useful visible error rather than a blank page.
    failed=browser.new_page()
    failed.route('**/data.json',lambda route: route.fulfill(status=503,body='Unavailable'))
    failed.goto('http://127.0.0.1:8000/',wait_until='networkidle')
    assert 'Could not load saved results' in failed.locator('#status').inner_text()
    summary={'browser':'headless Chromium','viewports':[1440,1024,768,390],
             'valid_configurations':len(data['series']),'selector_states_per_desktop_mobile':len(cases),
             'screenshots':[f'editorial-{w}.png' for w in [1440,1024,768,390]],
             'checks':['StationShift desktop/mobile branding','page title and description','renamed CSV filename','default measured MAE','all selectors','unsupported budgets','interval availability',
                       'CSV download','measured-values keyboard toggle','local fallback explanation','keyboard tab','keyboard chart scrolling','reduced motion','navigation anchors','four-width overflow',
                       'exact-state LightGBM deltas','coverage percentage-point sign','all valid and unsupported states','failed data request'],
             'page_errors':errors,'unexpected_http_errors':bad_responses,'passed':True}
    (out/'checks.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    browser.close()
