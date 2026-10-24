"""Step 5 scoping (2026-10-23): the engine's corn-soybean rotation (year_plan, soybean path passes mineral N and carbon through unchanged) against Cycles' own rotation (rotation_scope_2026_10_23.py output /tmp/w/rot_cycles.json), 24 sites, N=0 and 150 on corn, none on soybean."""
import os,sys,json
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E, engine_api as api
from multiprocessing import Pool
S=json.load(open(os.environ.get('SITES','/tmp/w/s24.json'))); TAG=os.environ.get('ROTTAG',''); orig=m.simulate_continuous
def patched(wx,crop,**kw):
    soy=dict(api._SOYBEAN_N if os.environ.get("LEGUME_N","0")=="1" else api._SOYBEAN); soy.update(lat_deg=crop["lat_deg"],make_layers=crop["make_layers"])
    ks={k:v for k,v in kw.items() if k not in ("n_rate_kg_ha","fertilizer_source","carry_n")}
    if os.environ.get("LEGUME_N","0")=="1":
        soy.update(**json.loads(os.environ.get("SOYKV","{}")))
        ks=dict(kw); ks.pop("carry_n",None); ks.update(n_rate_kg_ha=0); ks.pop("fertilizer_source",None)
    yp={y:(dict(crop=crop) if y%2==0 else dict(crop=soy,kw_replace=dict(ks))) for y in wx}
    return orig(wx,crop,year_plan=yp,**kw)
m.simulate_continuous=patched
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    r=m.engine(site,wx,soil,cl,N,'leadin')
    return site,N,{y:dict(grain=v.get("grain"),leach=v.get("n_leached_kg_ha"),denit=v.get("n_denitrified_kg_ha"),fix=v.get("n_fixed_kg_ha"),plantn=v.get("n_plant_kg_ha"),upt=v.get("n_uptake_kg_ha")) for y,v in r.items()}
if __name__=="__main__":
    R=Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150)]); C=json.load(open('/tmp/w/rot_cycles'+TAG+'.json'))
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
        fx=[v["fix"] for s,n,res in R if n==N for y,v in res.items() if y%2==1 and y>=1983 and v.get("fix") is not None]
        pn=[v["plantn"] for s,n,res in R if n==N for y,v in res.items() if y%2==1 and y>=1983 and v.get("plantn") is not None]
        up=[v["upt"] for s,n,res in R if n==N for y,v in res.items() if y%2==1 and y>=1983 and v.get("upt") is not None]
        if fx: print(f"   soybean engine fixation {np.mean(fx):.0f}, plant N {np.mean(pn):.0f}, soil uptake {np.mean(up):.0f} kg N/ha (Cycles 142 / 203 / 61)")
        for ph,par in (("corn yr",0),("soy yr",1)):
            lk=[v["leach"] for s,n,res in R if n==N for y,v in res.items() if y%2==par and y>=1983 and v.get("leach") is not None]
            dn=[v["denit"] for s,n,res in R if n==N for y,v in res.items() if y%2==par and y>=1983 and v.get("denit") is not None]
            cl=[];cd=[]
            for s,n,res in R:
                if n!=N: continue
                ay=C[f"{s}|{N}"][1]
                for y in res:
                    if y>=1983 and y%2==par and str(y) in ay: cl.append(float(ay[str(y)]["NO3_leaching"])+float(ay[str(y)]["NH4_leaching"])); cd.append(float(ay[str(y)]["denitrification"]))
            if lk: print(f"   {ph}: leaching engine {np.mean(lk):.1f} Cycles {np.mean(cl):.1f}; denitrification engine {np.mean(dn):.1f} Cycles {np.mean(cd):.1f}")
        per=[]
        for s_,n,res in R:
            if n!=N: continue
            ay=C[f"{s_}|{N}"][1]
            e=[v["fix"] for y,v in res.items() if y%2==1 and y>=1983 and v.get("fix") is not None]; c_=[float(ay[str(y)]["fixation"]) for y in res if y%2==1 and y>=1983 and str(y) in ay]
            if e and c_: per.append((s_,np.mean(e),np.mean(c_)))
        if per:
            a=np.array([[p[1],p[2]] for p in per]); print(f"   per-site mean fixation engine vs Cycles: corr {np.corrcoef(a.T)[0,1]:.2f}, engine min {a[:,0].min():.0f} Cycles min {a[:,1].min():.0f}, sites with engine<30 & Cycles>100: {int(((a[:,0]<30)&(a[:,1]>100)).sum())} of {len(a)}")
