"""Headless-Chromium test of simulator.html in real Pyodide 0.26.2. Serve the prototypes folder (python3 -m http.server 8765 --directory agricultural/prototypes), get the runtime with
`npm pack pyodide@0.26.2` extracted to /tmp/w/pyo_pkg (the container browser does not trust the egress proxy CA, so the CDN request is answered from those files; never disable certificate checks).
Run with playwright and the pre-installed Chromium."""
import time, glob, os, json
from playwright.sync_api import sync_playwright
ex=glob.glob('/opt/pw-browsers/chromium-*/chrome-linux*/chrome')[0]
PK='/tmp/w/pyo_pkg/package/'
def cdn(route):
    f=route.request.url.split('/full/')[-1].split('?')[0]; path=PK+f
    if os.path.isfile(path):
        ct={'js':'text/javascript','wasm':'application/wasm','zip':'application/zip','json':'application/json'}.get(f.rsplit('.',1)[-1],'application/octet-stream')
        route.fulfill(status=200,body=open(path,'rb').read(),headers={'content-type':ct,'access-control-allow-origin':'*'})
    else: route.fulfill(status=404,body='')
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=ex,proxy={"server":os.environ['HTTPS_PROXY'],"bypass":"localhost,127.0.0.1"}); pg=b.new_page()
    pg.route('https://cdn.jsdelivr.net/pyodide/**',cdn); pg.route('https://fonts.googleapis.com/**',lambda r:r.abort())
    errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto("http://localhost:8765/simulator.html")
    pg.wait_for_function("document.getElementById('status').textContent.startsWith('Choose')",timeout=240000)
    pg.click("#presets button:nth-child(1)")
    pg.wait_for_function("document.getElementById('siteInfo').textContent.includes('soil:')",timeout=120000)
    schema=pg.evaluate("SCHEMA")
    fields=[f for g in schema['groups'] for f in g['fields']]
    sel=[f for f in fields if f['type']=='select']; num=[f for f in fields if f['type']!='select']
    print("fields:",len(fields),"selects",len(sel),"numbers",len(num))
    def run(tag):
        pg.click("#runBtn")
        pg.wait_for_function("!document.getElementById('runBtn').disabled && document.getElementById('status').textContent!='Running...'",timeout=240000)
        st=pg.inner_text("#status"); rows=pg.eval_on_selector_all("#annualTable tr","t=>t.length-1")
        ok=st.startswith("Done") and rows>0
        if not ok: print("PROBLEM",tag,repr(st),rows)
        return ok
    bad=0; n=0
    def setv(fid,v):
        pg.evaluate("([i,v])=>{const e=document.getElementById('in_'+i); e.value=v; e.dispatchEvent(new Event('input',{bubbles:true}));}",[fid,str(v)])
    for crop in ['corn','wheat']:
        setv('crop',crop)
        for f in sel:
            if f['id']=='crop': continue
            base=pg.evaluate("i=>document.getElementById('in_'+i).value",f['id'])
            for o in f['options']:
                if str(o[0])==str(f['default']): continue
                setv(f['id'],o[0])
                if pg.evaluate("i=>{const e=document.getElementById('in_'+i); return e&&!e.closest('.f').classList.contains('hidden')&&!e.closest('fieldset').classList.contains('hidden')}",f['id']):
                    n+=1; bad+= (not run(f"{crop}:{f['id']}={o[0]}"))
            setv(f['id'],base)
    print("select variations run:",n,"problems:",bad)
    # numeric extremes (min and max) for corn
    setv('crop','corn'); nb=0; m=0
    for f in num:
        base=pg.evaluate("i=>document.getElementById('in_'+i).value",f['id'])
        for v in (f.get('min'),f.get('max')):
            if v is None: continue
            setv(f['id'],v)
            if pg.evaluate("i=>{const e=document.getElementById('in_'+i); return e&&!e.closest('.f').classList.contains('hidden')&&!e.closest('fieldset').classList.contains('hidden')}",f['id']):
                m+=1; nb+= (not run(f"corn:{f['id']}={v}"))
        setv(f['id'],base)
    print("numeric extremes run:",m,"problems:",nb,"page errors:",errs[:5])
    b.close()
