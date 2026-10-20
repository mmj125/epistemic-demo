"""Exact-output regression snapshot through engine_api (2026-10-20). `python3 snapshot_2026_10_20.py save FILE` records, `... check FILE` compares (must be identical for a pure code deletion).
Covers three sites, five crops, N 0 and 150, and each input option (split N, urea, manure, tillage, irrigation, planting window)."""
import sys,json,hashlib
sys.path.insert(0,'.')
import field_data as fd, engine_api as api
F=["pp","tx","tn","solar","rhx","rhn","wind"]
SITES={"Iowa":(42.0,-93.6),"Kansas":(37.97,-100.87),"MD":(38.5,-75.8)}
def cases():
    for s in SITES:
        for crop in ("corn","silage","sorghum","soybean","wheat"):
            for n in (0,150): yield s,dict(crop=crop,n_rate=n)
    yield "Iowa",dict(crop="corn",n_rate=150,n_timing="split",n_doy1=100,n_frac1=40,n_doy2=170)
    yield "Iowa",dict(crop="corn",n_rate=150,fert_source="urea")
    yield "Iowa",dict(crop="corn",n_rate=150,fert_source="anhydrous_ammonia",manure_n=100)
    yield "Iowa",dict(crop="corn",n_rate=150,tillage_implement="Plow_moldboard",tillage_when="planting")
    yield "Iowa",dict(crop="corn",n_rate=150,tillage_implement="Chisel_sweep_shovel",tillage_when="day",tillage_doy=140)
    yield "Kansas",dict(crop="sorghum",n_rate=100,irrigation_on="auto",irrigation_trigger=0.5,irrigation_mm=25)
    yield "MD",dict(crop="soybean",plant_min_doy=130,plant_max_doy=150,irrigation_on="auto")
    yield "Iowa",dict(crop="wheat",n_rate=90,n_timing="split",n_doy1=289,n_frac1=40,n_doy2=75)
def run_all():
    out={}; cur=None
    for i,(s,cfg) in enumerate(cases()):
        if s!=cur:
            lat,lon=SITES[s]; wx,_=fd.resolve_field_weather(lat,lon); soil,_,_=fd.resolve_field_soil(lat,lon)
            api.load_site(json.dumps(dict(lat=lat,weather=dict(fields=F,years={str(y):{str(d):[r[k] for k in F] for d,r in days.items()} for y,days in wx.items() if y<=1992}),soil=soil))); cur=s
        c=dict(start_year=1980,end_year=1992,**cfg); r=json.loads(api.run(json.dumps(c)))
        h=hashlib.sha256(json.dumps(r["daily"],sort_keys=True).encode()).hexdigest()[:16]
        out[f"{i}|{s}|{json.dumps(cfg,sort_keys=True)}"]=dict(annual=r["annual"],daily=h)
    return out
if __name__=="__main__":
    mode,fn=sys.argv[1],sys.argv[2]
    if mode=="save": json.dump(run_all(),open(fn,"w")); print("saved",fn)
    else:
        a=json.load(open(fn)); b=run_all(); bad=[k for k in a if a[k]!=b.get(k)]
        print("IDENTICAL" if not bad and a.keys()==b.keys() else f"DIFFERENT in {len(bad)} cases: {bad[:3]}")
