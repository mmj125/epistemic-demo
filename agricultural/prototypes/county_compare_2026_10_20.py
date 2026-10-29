"""Engine and Cycles against USDA NASS county yields, fresh94 sites (2026-10-20). Observed: data/nass_county_yield_fresh94.csv (county containing the site point,
sitesets/fresh94_county.json). Engine: /tmp/w/engine_county_runs.json (county_runs_2026_10_20.py). Cycles: reference cache in /tmp/cycles-run15 (same weather, soil, N).
Reports (1) within-site agreement of detrended year-to-year yield, (2) pooled standardized anomalies, (3) site-to-site spatial pattern, (4) yield level, for engine and Cycles against observations."""
import json,glob,os,sys
import numpy as np, pandas as pd
CY="/tmp/cycles-run15"
sc=json.load(open('sitesets/fresh94_county.json')); eng=json.load(open(os.environ.get('ENGRUN','/tmp/w/engine_county_runs.json')))
obs=pd.read_csv('data/nass_county_yield_fresh94.csv',dtype={'fips':str})
Y0,Y1=1982,2016
CROPS={"corn":dict(sel=lambda d:(d.COMMODITY_DESC=="CORN")&(d.UTIL_PRACTICE_DESC=="GRAIN")&(d.PRODN_PRACTICE_DESC=="ALL PRODUCTION PRACTICES")&(d.UNIT_DESC=="BU / ACRE"),conv=0.062770,cy=lambda s:f"{s}N150"),
       "soybean":dict(sel=lambda d:(d.COMMODITY_DESC=="SOYBEANS")&(d.PRODN_PRACTICE_DESC=="ALL PRODUCTION PRACTICES")&(d.UNIT_DESC=="BU / ACRE"),conv=0.067250,cy=lambda s:f"{s}soyN0"),
       "wheat":dict(sel=lambda d:(d.COMMODITY_DESC=="WHEAT")&(d.CLASS_DESC=="WINTER")&(d.PRODN_PRACTICE_DESC=="ALL PRODUCTION PRACTICES")&(d.UNIT_DESC=="BU / ACRE"),conv=0.067250,cy=lambda s:f"{s}wheatF60N150"),
       "silage":dict(sel=lambda d:(d.COMMODITY_DESC=="CORN")&(d.UTIL_PRACTICE_DESC=="SILAGE")&(d.UNIT_DESC=="TONS / ACRE"),conv=2.2417*0.35,cy=lambda s:f"{s}silN150")}
def cyc(name):
    f=f"{CY}/cache15_{name}.json"
    if not os.path.exists(f): return None
    H=json.load(open(f))["H"]; return {int(y):(v["grain"]) for y,v in H.items()}
def detrend(y,x):
    p=np.polyfit(x,y,1); return y-np.polyval(p,x)
def stats(crop,cfg):
    d=obs[cfg["sel"](obs)]; rows=[]
    HALF=os.environ.get('HALF')   # 'dev' = even positions of the sorted site list, 'test' = odd (EVALUATION_PROTOCOL_2026_10_28.md)
    order={k:i for i,k in enumerate(sorted(sc))}
    for site,c in sc.items():
        if HALF and (order[site]%2==0)!=(HALF=='dev'): continue
        if not c["fips"] or site not in eng or crop not in eng[site] or "error" in eng[site][crop]: continue
        o=d[d.fips==c["fips"]].groupby("YEAR")["VALUE"].mean()*cfg["conv"]
        e={int(k):v for k,v in eng[site][crop].items()}; cy=cyc(cfg["cy"](site))
        if cy is None: continue
        yrs=[y for y in range(Y0,Y1+1) if y in o.index and e.get(y) is not None and (cy is None or cy.get(y) is not None)]
        if len(yrs)<15: continue
        yrs=np.array(yrs); ov=np.array([o[y] for y in yrs]); ev=np.array([e[y] for y in yrs]); cv=np.array([cy[y] for y in yrs]) if cy else None
        rows.append(dict(site=site,lon=c["lon"],n=len(yrs),yrs=yrs,o=ov,e=ev,c=cv))
    return rows
def report(crop,rows,label):
    if not rows: print(f"{crop} {label}: no sites"); return
    out={}
    for who in ("e","c"):
        if rows[0][who] is None: continue
        wc=[]; z_o=[]; z_m=[]; mo=[]; mm=[]
        for r in rows:
            ao=detrend(r["o"],r["yrs"]); am=detrend(r[who],r["yrs"])
            if ao.std()>1e-9 and am.std()>1e-9: wc.append(np.corrcoef(ao,am)[0,1]); z_o.append(ao/ao.std()); z_m.append(am/am.std())
            sel=r["yrs"]>=2007; mo.append(r["o"][sel].mean() if sel.any() else np.nan); mm.append(r[who][sel].mean() if sel.any() else np.nan)
        mo,mm=np.array(mo),np.array(mm); ok=~np.isnan(mo)&~np.isnan(mm)
        out[who]=dict(within=np.nanmedian(wc),within_mean=np.nanmean(wc),pooled=np.corrcoef(np.concatenate(z_o),np.concatenate(z_m))[0,1],spatial=np.corrcoef(mo[ok],mm[ok])[0,1],level=np.nanmedian(mm[ok]/mo[ok]),mo=np.nanmean(mo[ok]),mm=np.nanmean(mm[ok]),n=len(rows))
    print(f"{crop:8s} {label:10s} sites {len(rows):3d} | "+" | ".join(f"{('engine' if w=='e' else 'Cycles'):6s} within-site r {v['within']:+.2f} (mean {v['within_mean']:+.2f}) pooled r {v['pooled']:+.2f} spatial r {v['spatial']:+.2f} level x{v['level']:.2f} (obs {v['mo']:.2f} model {v['mm']:.2f} Mg/ha)" for w,v in out.items()))
for crop,cfg in CROPS.items():
    if os.environ.get('ONLYCROP') and crop!=os.environ['ONLYCROP']: continue
    rows=stats(crop,cfg)
    report(crop,rows,"all"); report(crop,[r for r in rows if r["lon"]>-97.5],"east -97.5"); report(crop,[r for r in rows if r["lon"]<=-97.5],"west")
print("\nPaired difference in within-site detrended correlation, engine minus Cycles (bootstrap over sites), and extreme years (corn, east of -97.5, % deviation from each series' own trend)")
rng=np.random.default_rng(0)
for crop,cfg in CROPS.items():
    if os.environ.get('ONLYCROP') and crop!=os.environ['ONLYCROP']: continue
    rows=[r for r in stats(crop,cfg)]
    d=[]
    for r in rows:
        ao=detrend(r["o"],r["yrs"]); ae=detrend(r["e"],r["yrs"]); ac=detrend(r["c"],r["yrs"])
        if min(ao.std(),ae.std(),ac.std())>1e-9: d.append(np.corrcoef(ao,ae)[0,1]-np.corrcoef(ao,ac)[0,1])
    d=np.array(d); bs=d[rng.integers(0,len(d),(4000,len(d)))].mean(1)
    print(f" {crop:8s} engine - Cycles within-site r: {d.mean():+.3f} [{np.percentile(bs,2.5):+.3f},{np.percentile(bs,97.5):+.3f}] over {len(d)} sites")
rows=[r for r in stats("corn",CROPS["corn"]) if r["lon"]>-97.5]
for yr in (1983,1988,1993,2012):
    v={"obs":[],"engine":[],"Cycles":[]}
    for r in rows:
        if yr in r["yrs"]:
            i=list(r["yrs"]).index(yr)
            for k,a in (("obs","o"),("engine","e"),("Cycles","c")):
                tr=np.polyval(np.polyfit(r["yrs"],r[a],1),yr); v[k].append(100*(r[a][i]-tr)/tr)
    print(f" {yr}: "+"  ".join(f"{k} {np.mean(x):+.0f}%" for k,x in v.items())+f"  ({len(v['obs'])} sites)")
