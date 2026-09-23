"""Standalone headless fallback when the in-app browser is unavailable."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
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
    assert page.locator('.brand').inner_text()=='StationShift'
    assert page.locator('meta[name="description"]').get_attribute('content')=='When do time-series foundation models transfer to a new environmental monitoring station?'
    assert page.locator('#mae').inner_text()=='55.94'
    assert page.locator('#station option').count()==12
    page.screenshot(path=str(out/'desktop.png'),full_page=True)
    page.locator('#station').select_option('Wanliu')
    page.locator('#horizon').select_option('6')
    page.locator('#history').select_option('2160')
    data=json.loads((ROOT/'site/data.json').read_text())
    expected=data['series']['Wanliu|Chronos-2|2160|6']
    assert page.locator('#mae').inner_text()==f"{expected['mae']:.2f}"
    assert page.locator('#rows tr').count()==len(expected['rows'])
    page.locator('#history').select_option('0')
    assert page.locator('#result').is_hidden() and 'requires local observations' in page.locator('#status').inner_text()
    page.locator('#model').select_option('LightGBM calendar')
    assert page.locator('#result').is_visible()
    assert page.locator('#coverage').inner_text()=='Not available'
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
    page.screenshot(path=str(out/'mobile.png'),full_page=True)
    assert not errors, errors
    assert not bad_responses, bad_responses
    # Actual failed-resource path also gives a useful visible error rather than a blank page.
    failed=browser.new_page()
    failed.route('**/data.json',lambda route: route.fulfill(status=503,body='Unavailable'))
    failed.goto('http://127.0.0.1:8000/',wait_until='networkidle')
    assert 'Could not load saved results' in failed.locator('#status').inner_text()
    summary={'browser':'headless Chromium','desktop':'1440x1100','mobile':'390x844',
             'checks':['StationShift desktop/mobile branding','page title and description','renamed CSV filename','default measured MAE','all selectors','unsupported budgets','interval availability',
                       'CSV download','local fallback explanation','keyboard tab','mobile overflow','failed data request'],
             'page_errors':errors,'unexpected_http_errors':bad_responses,'passed':True}
    (out/'checks.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    browser.close()
