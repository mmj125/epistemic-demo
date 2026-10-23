"""Step 5 scoping (2026-10-23): the engine's corn-soybean rotation (year_plan, soybean path passes mineral N and carbon through unchanged) against Cycles' own rotation (rotation_scope_2026_10_23.py output /tmp/w/rot_cycles.json), 24 sites, N=0 and 150 on corn, none on soybean."""
import os,sys,json
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E, engine_api as api
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); orig=m.simulate_continuous
def patched(wx,crop,**kw):
    soy=dict(api._SOYBEAN); soy.update(lat_deg=crop["lat_deg"],make_layers=crop["make_layers"])
    ks={k:v for k,v in kw.items() if k not in ("n_rate_kg_ha","fertilizer_source","carry_n")}
    yp={y:(dict(crop=crop) if y%2==0 else dict(crop=soy,kw_replace=dict(ks))) for y in wx}
    return orig(wx,crop,year_plan=yp,**kw)
m.simulate_continuous=patched
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    r=m.engine(site,wx,soil,cl,N,'leadin')
    return site,N,{y:dict(grain=v.get("grain"),leach=v.get("n_leached_kg_ha"),denit=v.get("n_denitrified_kg_ha")) for y,v in r.items()}
if __name__=="__main__":
    R=Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150)]); C=json.load(open('/tmp/w/rot_cycles.json'))
    for N in (0,150):
        e=[];c=[];es=[];cs=[];el=[];cl_=[]
        for s,n,res in R:
            if n!=N: continue
            hy,ay=C[f"{s}|{N}"]
            for y,v in res.items():
                if y<1983 or str(y) not in hy: continue
                g=hy[str(y)][1]
                if y%2==0 and v["grain"] is not None: e.append(v["grain"]); c.append(g); 
                if y%2==1 and v["grain"] is not None: es.append(v["grain"]); cs.append(g)
        e,c,es,cs=map(np.array,(e,c,es,cs))
        print(f"N={N}: corn after soy engine {e.mean():.2f} Cycles {c.mean():.2f} (ratio {e.mean()/c.mean():.2f}, MAE {np.abs(e-c).mean():.2f}, corr {np.corrcoef(e,c)[0,1]:.3f}); soybean engine {es.mean() if len(es) else float('nan'):.2f} Cycles {cs.mean() if len(cs) else float('nan'):.2f}")
