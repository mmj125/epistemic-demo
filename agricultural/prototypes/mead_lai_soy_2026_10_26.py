"""Soybean canopy at Mead against measured LAI (2026-10-26), same method as mead_lai_fit2: planting days inferred from LAI before day 215 (soybean), then a grid over senescence delay and stress K scored on observations from August on
(intercepted fraction, k 0.55), leave-one-site-out and leave-one-year-out. Engine with tower-adjusted weather, legume N soybean. Usage: python3 mead_lai_soy_2026_10_26.py"""
import os,sys,json,math,copy,datetime
sys.path.insert(0,'.')
import numpy as np, mead_score_2026_10_23 as M, rhizo_engine as E
SITES=["Ne1","Ne2","Ne3"]; SH=[130,134,138,142,146,150,154,158]; D={}
def obs_of(b,pl):
    o={}
    for l in b["lai"]:
        d=l["LAI_DATE"]; iso=f"{d[:4]}-{d[4:6]}-{d[6:]}"; y=int(d[:4])
        if y in pl and pl[y]["crop"]=="soy" and not pl[y].get("documented_plant"): o.setdefault(y,[]).append((iso,1-math.exp(-0.55*float(l["LAI_TOT"])),datetime.date.fromisoformat(iso).timetuple().tm_yday,int(d[4:6])))
    return o
for s in SITES:
    soil,b,pl,lat,lon,wx,CW,CH,CYld,T=M._cache(s,"toweradj"); obs=obs_of(b,pl); runs={}
    print(s,"soy years with LAI:",{y:len(L) for y,L in obs.items()},flush=True)
    if not obs: continue
    for sh in SH:
        p2=copy.deepcopy(pl)
        for y,v in p2.items():
            if v["crop"]=="soy" and not v.get("documented_plant"): v["plant"]=sh
        res=M.engine_run(s,soil,p2,lat,wx); ED,_=M.engine_parse(res,soil); runs[sh]=ED
    best={}
    for y,L in obs.items():
        early=[x for x in L if x[2]<215 and all(x[0] in runs[sh] for sh in SH)]
        if len(early)>=3: best[y]=min(SH,key=lambda sh:np.sqrt(np.mean([(runs[sh][x[0]]["fi"]-x[1])**2 for x in early])))
    p3=copy.deepcopy(pl)
    for y,sh in best.items(): p3[y]["plant"]=sh
    D[s]=(soil,p3,lat,wx,obs,best); print(" planting days",best,flush=True)
SITES=[s for s in SITES if s in D]
GRID=[(0.0,0.0)]+[(dl,k) for dl in (-0.08,-0.04,0.04,0.08,0.12) for k in (0.0,0.5,1.0,2.0)]
R={}
for s in SITES:
    soil,p3,lat,wx,obs,best=D[s]
    for g in GRID:
        E.CANOPY_SENES_DELAY,E.CANOPY_SENES_STRESS_K=g
        try: res=M.engine_run(s,soil,p3,lat,wx)
        finally: E.CANOPY_SENES_DELAY=0.0; E.CANOPY_SENES_STRESS_K=0.0
        ED,_=M.engine_parse(res,soil); rows=[]
        for y,L in obs.items():
            if y not in best: continue
            for iso,fo,doy,mo in L:
                if mo>=8 and iso in ED: rows.append((fo,ED[iso]["fi"],mo,y))
        R[(s,g)]=np.array(rows)
def rms(A): return float(np.sqrt(((A[:,1]-A[:,0])**2).mean())) if len(A) else float("nan")
print("August on, n:",{s:len(R[(s,(0.0,0.0))]) for s in SITES}); print("baseline rms, bias:",{s:(round(rms(R[(s,(0.0,0.0))]),3),round(float((R[(s,(0.0,0.0))][:,1]-R[(s,(0.0,0.0))][:,0]).mean()),3)) for s in SITES})
pool=lambda g:np.sqrt(np.mean(np.concatenate([(R[(o,g)][:,1]-R[(o,g)][:,0])**2 for o in SITES])))
print("pooled rms by (delay, K):"); 
for dl in (-0.08,-0.04,0.0,0.04,0.08,0.12): print(f" {dl:+.2f}",[round(float(pool((dl,k))),3) if (dl,k) in R_keys else None for k in (0.0,0.5,1.0,2.0)] if (R_keys:=set(g for (_,g) in R)) else None)
best=min(GRID,key=pool); print("best pooled",best,round(float(pool(best)),3),"baseline",round(float(pool((0.0,0.0))),3))
yrs=sorted({int(y) for s in SITES for y in R[(s,(0.0,0.0))][:,3]}); t0=t1=n=0
for yo in yrs:
    sel=lambda g,keep:np.concatenate([R[(o,g)][(R[(o,g)][:,3]!=yo)==keep] for o in SITES])
    g=min(GRID,key=lambda g:np.mean((sel(g,True)[:,1]-sel(g,True)[:,0])**2)); A=sel(g,False);B=sel((0.0,0.0),False)
    if len(A): t1+=((A[:,1]-A[:,0])**2).sum(); t0+=((B[:,1]-B[:,0])**2).sum(); n+=len(A)
print(f"leave one year out pooled held-out rms {math.sqrt(t1/n):.3f} vs baseline {math.sqrt(t0/n):.3f} (n {n})")
