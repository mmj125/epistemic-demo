"""Headless Chromium check of the About panel, the run record download and the layout at desktop and phone width (2026-10-24). Same setup as simulator_pyodide_test.py (npm Pyodide copy at /tmp/w/pyo_pkg, page served on :8765)."""
import os, glob, json, time
from playwright.sync_api import sync_playwright
ex=glob.glob('/opt/pw-browsers/chromium-*/chrome-linux*/chrome')[0]; PK='/tmp/w/pyo_pkg/package/'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=ex,proxy={"server":os.environ['HTTPS_PROXY'],"bypass":"localhost,127.0.0.1"})
    for label,vp in (("desktop",dict(width=1100,height=900)),("phone",dict(width=390,height=844))):
        pg=b.new_page(viewport=vp,accept_downloads=True)
        def cdn(route):
            f=route.request.url.split('/full/')[-1].split('?')[0]; path=PK+f
            if os.path.isfile(path):
                ct={'js':'text/javascript','wasm':'application/wasm','zip':'application/zip','json':'application/json'}.get(f.rsplit('.',1)[-1],'application/octet-stream')
                route.fulfill(status=200,body=open(path,'rb').read(),headers={'content-type':ct,'access-control-allow-origin':'*'})
            else: route.fulfill(status=404,body='')
        pg.route('https://cdn.jsdelivr.net/pyodide/**',cdn); pg.route('https://fonts.googleapis.com/**',lambda r:r.abort())
        errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)))
        pg.goto("http://localhost:8765/simulator.html")
        pg.wait_for_function("document.getElementById('status').textContent.startsWith('Choose') || document.getElementById('status').textContent.startsWith('Engine failed')",timeout=180000)
        print(label,"title:",pg.title(),"| h1:",pg.inner_text("#modelName"))
        pg.click("#aboutDetails summary")
        print(label,"about: rows in validation table",pg.eval_on_selector_all("#aboutBody table tr","t=>t.length"),"| limitations",pg.eval_on_selector_all("#aboutBody ul li","l=>l.length"))
        pg.click("#presets button:nth-child(2)")
        pg.wait_for_function("document.getElementById('siteInfo').textContent.includes('soil:')",timeout=120000)
        pg.click("#runBtn"); pg.wait_for_function("!document.getElementById('results').classList.contains('hidden') && document.getElementById('status').textContent.startsWith('Done')",timeout=240000)
        with pg.expect_download() as d: pg.click("#dlRecord")
        path=d.value.path(); rec=json.load(open(path)); print(label,"record keys:",sorted(rec.keys()),"| annual rows",len(rec["annual"]),"| site",rec["site"])
        sw=pg.evaluate("document.documentElement.scrollWidth"); print(label,"scrollWidth",sw,"viewport",vp["width"])
        pg.screenshot(path=f"/tmp/w/sim_{label}.png",full_page=False)
        print(label,"errors:",[e for e in errs][:3]); pg.close()
    b.close()
