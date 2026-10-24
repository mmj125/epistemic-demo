"""Loads the LIVE GitHub Pages simulator in headless Chromium and runs corn and wheat (2026-10-24). The container browser does not trust the egress proxy CA, so every request to the site is fetched with Python (proxy CA bundle) and handed to the page; Pyodide comes from the npm copy at /tmp/w/pyo_pkg. Never disables certificate checks."""
import os, glob, time, ssl, urllib.request
from playwright.sync_api import sync_playwright
BASE="https://mmj125.github.io"; ex=glob.glob('/opt/pw-browsers/chromium-*/chrome-linux*/chrome')[0]; PK='/tmp/w/pyo_pkg/package/'
ctx=ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt'); proxy=urllib.request.ProxyHandler({'https':os.environ['HTTPS_PROXY']}); op=urllib.request.build_opener(proxy,urllib.request.HTTPSHandler(context=ctx))
def live(route):
    u=route.request.url
    try:
        r=op.open(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=120); body=r.read(); route.fulfill(status=r.status,body=body,headers={'content-type':r.headers.get('content-type','application/octet-stream'),'access-control-allow-origin':'*'})
    except Exception as e: route.fulfill(status=404,body=str(e))
def cdn(route):
    f=route.request.url.split('/full/')[-1].split('?')[0]; path=PK+f
    if os.path.isfile(path):
        ct={'js':'text/javascript','wasm':'application/wasm','zip':'application/zip','json':'application/json'}.get(f.rsplit('.',1)[-1],'application/octet-stream'); route.fulfill(status=200,body=open(path,'rb').read(),headers={'content-type':ct,'access-control-allow-origin':'*'})
    else: route.fulfill(status=404,body='')
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=ex); pg=b.new_page()
    pg.route(BASE+'/**',live); pg.route('https://cdn.jsdelivr.net/pyodide/**',cdn); pg.route('https://fonts.googleapis.com/**',lambda r:r.abort())
    errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)))
    t0=time.time(); pg.goto(BASE+"/epistemic-demo/agricultural/prototypes/simulator.html")
    pg.wait_for_function("document.getElementById('status').textContent.startsWith('Choose') || document.getElementById('status').textContent.startsWith('Engine failed')",timeout=240000)
    print("title:",pg.title(),"| h1:",pg.inner_text("#modelName"),"| status:",pg.inner_text("#status"),"| load",round(time.time()-t0,1),"s")
    pg.click("#aboutDetails summary"); print("about table rows:",pg.eval_on_selector_all("#aboutBody table tr","t=>t.length"))
    pg.click("#presets button:nth-child(2)"); pg.wait_for_function("document.getElementById('siteInfo').textContent.includes('soil:')",timeout=240000); print("site:",pg.inner_text("#siteInfo")[:90])
    for crop in ("corn","wheat","rotation"):
        pg.select_option("#in_crop",crop); pg.dispatch_event("#controls","input"); t=time.time(); pg.click("#runBtn")
        pg.wait_for_function("document.getElementById('status').textContent.startsWith('Done') || document.getElementById('status').textContent.startsWith('Error')",timeout=300000)
        rows=pg.eval_on_selector_all("#annualTable tr","trs=>trs.map(r=>[...r.children].map(c=>c.textContent.trim()))")
        print(crop,pg.inner_text("#status"),"rows",len(rows)-1,rows[1][:6],"mean row",rows[-1][:6]); pg.evaluate("document.getElementById('status').textContent='x'")
    print("page errors:",errs[:3]); b.close()
