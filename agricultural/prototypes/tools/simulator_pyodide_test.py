"""Headless-Chromium test of simulator.html in real Pyodide 0.26.2. Serve the prototypes folder (python3 -m http.server 8765 --directory agricultural/prototypes), get the runtime with
`npm pack pyodide@0.26.2` extracted to /tmp/w/pyo_pkg (the container browser does not trust the egress proxy CA, so the CDN request is answered from those files; never disable certificate checks).
Run with playwright and the pre-installed Chromium."""
import time, json, glob
from playwright.sync_api import sync_playwright
ex=glob.glob('/opt/pw-browsers/chromium-*/chrome-linux*/chrome')[0]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=ex,proxy={"server":__import__('os').environ['HTTPS_PROXY'],"bypass":"localhost,127.0.0.1"}); pg=b.new_page()
    import os, mimetypes
    PK='/tmp/w/pyo_pkg/package/'
    def cdn(route):
        f=route.request.url.split('/full/')[-1].split('?')[0]
        path=PK+f
        if os.path.isfile(path):
            ct={'js':'text/javascript','wasm':'application/wasm','zip':'application/zip','json':'application/json'}.get(f.rsplit('.',1)[-1],'application/octet-stream')
            route.fulfill(status=200,body=open(path,'rb').read(),headers={'content-type':ct,'access-control-allow-origin':'*'})
        else: route.fulfill(status=404,body='')
    pg.route('https://cdn.jsdelivr.net/pyodide/**',cdn)
    pg.route('https://fonts.googleapis.com/**',lambda r:r.abort())
    errs=[]; pg.on("pageerror",lambda e:errs.append("PAGEERR "+str(e))); pg.on("console",lambda m: errs.append("CONSOLE "+m.text[:300]) if m.type=="error" else None)
    pg.on("requestfailed",lambda r: errs.append("REQFAIL "+r.url[:120]))
    t0=time.time(); pg.goto("http://localhost:8765/simulator.html")
    pg.wait_for_function("document.getElementById('status').textContent.startsWith('Engine failed') || document.getElementById('status').textContent.startsWith('Choose') || document.getElementById('status').textContent.startsWith('Ready')",timeout=240000)
    print("engine load s:",round(time.time()-t0,1),"|",pg.inner_text("#status"))
    pg.click("#presets button:nth-child(2)")
    pg.wait_for_function("document.getElementById('siteInfo').textContent.includes('soil:') || document.getElementById('siteInfo').className=='err'",timeout=120000)
    print("site:",pg.inner_text("#siteInfo")[:140])
    crops=pg.eval_on_selector("#in_crop","s=>[...s.options].map(o=>o.value)")
    print("crops:",crops)
    for c in crops:
        pg.select_option("#in_crop",c); pg.dispatch_event("#controls","input")
        t=time.time(); pg.click("#runBtn")
        try:
            pg.wait_for_function("!document.getElementById('results').classList.contains('hidden') && document.getElementById('status').textContent!='Running...'",timeout=240000)
        except Exception as e: print(c,"TIMEOUT",pg.inner_text("#status"))
        dt=time.time()-t
        rows=pg.eval_on_selector_all("#annualTable tr","trs=>trs.map(r=>[...r.children].map(c=>c.textContent.trim()))")
        print(f"{c:10s} run {dt:5.1f}s status={pg.inner_text('#status')!r} rows={len(rows)-1}",rows[1][:6] if len(rows)>1 else rows)
        pg.evaluate("document.getElementById('results').classList.add('hidden')")
    print("errors:",errs[:8])
    b.close()
