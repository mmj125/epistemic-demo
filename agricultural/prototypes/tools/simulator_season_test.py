"""Headless Chromium check of the Daily tab season view for corn and winter wheat (2026-10-24). Same setup as simulator_about_test.py (npm Pyodide copy at /tmp/w/pyo_pkg, page served on :8765)."""
import os, glob
from playwright.sync_api import sync_playwright
ex=glob.glob('/opt/pw-browsers/chromium-*/chrome-linux*/chrome')[0]; PK='/tmp/w/pyo_pkg/package/'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=ex,proxy={"server":os.environ['HTTPS_PROXY'],"bypass":"localhost,127.0.0.1"})
    pg=b.new_page(viewport=dict(width=1100,height=1000))
    def cdn(route):
        f=route.request.url.split('/full/')[-1].split('?')[0]; path=PK+f
        if os.path.isfile(path):
            ct={'js':'text/javascript','wasm':'application/wasm','zip':'application/zip','json':'application/json'}.get(f.rsplit('.',1)[-1],'application/octet-stream')
            route.fulfill(status=200,body=open(path,'rb').read(),headers={'content-type':ct,'access-control-allow-origin':'*'})
        else: route.fulfill(status=404,body='')
    pg.route('https://cdn.jsdelivr.net/pyodide/**',cdn); pg.route('https://fonts.googleapis.com/**',lambda r:r.abort())
    errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto("http://localhost:8765/simulator.html")
    pg.wait_for_function("document.getElementById('status').textContent.startsWith('Choose')",timeout=180000)
    pg.click("#presets button:nth-child(2)"); pg.wait_for_function("document.getElementById('siteInfo').textContent.includes('soil:')",timeout=120000)
    for crop in ("corn","wheat"):
        pg.select_option("#in_crop",crop); pg.dispatch_event("#controls","input"); pg.click("#runBtn")
        pg.wait_for_function("document.getElementById('status').textContent.startsWith('Done')",timeout=300000)
        pg.click('[data-tab=daily]'); pg.wait_for_timeout(500)
        pg.locator("#seasonCanvas").screenshot(path=f"/tmp/w/season_{crop}.png"); print(crop,"ok"); pg.evaluate("document.getElementById('status').textContent='x'")
    print("errors:",errs[:3]); b.close()
