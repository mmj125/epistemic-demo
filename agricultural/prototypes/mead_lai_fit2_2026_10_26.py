"""Senescence stress law against Mead LAI with planting days inferred from the early LAI (2026-10-26). Step 1: per site-year planting day (121 to 142) matching LAI observed before day 195 (expansion only), documented shape. Step 2: with those days fixed,
grid over CANOPY_SENES_DELAY and CANOPY_SENES_STRESS_K, scored on observations from July on (senescence period), intercepted fraction, k 0.55; leave-one-site-out. Engine with tower-adjusted weather. Usage: python3 mead_lai_fit2_2026_10_26.py"""
import os,sys,json,math,copy,datetime
sys.path.insert(0,'.')
import numpy as np, mead_score_2026_10_23 as M, rhizo_engine as E
SITES=["Ne1","Ne2","Ne3"]; SH=[121,124,127,130,133,136,139,142]; D={}
def obs_of(b,pl):
    o={}
    for l in b["lai"]:
        d=l["LAI_DATE"]; iso=f"{d[:4]}-{d[4:6]}-{d[6:]}"; y=int(d[:4])
        if y in pl and pl[y]["crop"]=="corn" and not pl[y].get("documented_plant"): o.setdefault(y,[]).append((iso,1-math.exp(-0.55*float(l["LAI_TOT"])),datetime.date.fromisoformat(iso).timetuple().tm_yday,int(d[4:6])))
    return o
for s in SITES:
    soil,b,pl,lat,lon,wx,CW,CH,CYld,T=M._cache(s,"toweradj"); obs=obs_of(b,pl); runs={}
    for sh in SH:
        p2=copy.deepcopy(pl)
        for y,v in p2.items():
            if v["crop"]=="corn" and not v.get("documented_plant"): v["plant"]=sh
        res=M.engine_run(s,soil,p2,lat,wx); ED,_=M.engine_parse(res,soil); runs[sh]=ED
    best={}
    for y,L in obs.items():
        early=[x for x in L if x[2]<195 and all(x[0] in runs[sh] for sh in SH)]
        if len(early)>=3: best[y]=min(SH,key=lambda sh:np.sqrt(np.mean([(runs[sh][x[0]]["fi"]-x[1])**2 for x in early])))
    p3=copy.deepcopy(pl)
    for y,sh in best.items(): p3[y]["plant"]=sh
    D[s]=(soil,p3,lat,wx,obs,best); print(s,"planting days",best,flush=True)
GRID=[(0.0,0.0)]+[(dl,k) for dl in (0.04,0.08,0.12,0.16,0.20) for k in (0.0,0.25,0.5,0.75,1.0)]
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
                if mo>=7 and iso in ED: rows.append((fo,ED[iso]["fi"],mo,y))
        R[(s,g)]=np.array(rows)
def rms(A): return float(np.sqrt(((A[:,1]-A[:,0])**2).mean()))
print("senescence-period scores (July on), n per site:",{s:len(R[(s,(0.0,0.0))]) for s in SITES})
print("baseline: rms and bias (model minus observed)",{s:(round(rms(R[(s,(0.0,0.0))]),3),round(float((R[(s,(0.0,0.0))][:,1]-R[(s,(0.0,0.0))][:,0]).mean()),3)) for s in SITES})
print("rms pooled over sites, rows delay, columns K 0 0.5 1 2 3 4")
for dl in (0.04,0.08,0.12,0.16,0.20): print(f" {dl:+.2f}",[round(float(np.sqrt(np.mean(np.concatenate([(R[(o,(dl,k))][:,1]-R[(o,(dl,k))][:,0])**2 for o in SITES])))),3) for k in (0.0,0.25,0.5,0.75,1.0)])
print("leave one site out (parameters from the other two):")
for s in SITES:
    others=[o for o in SITES if o!=s]
    g=min(GRID,key=lambda g:np.sqrt(np.mean(np.concatenate([(R[(o,g)][:,1]-R[(o,g)][:,0])**2 for o in others]))))
    A=R[(s,g)];B=R[(s,(0.0,0.0))]; print(f" held out {s}: chosen delay {g[0]:+.2f} K {g[1]:.1f} | rms {rms(A):.3f} (baseline {rms(B):.3f}) bias {(A[:,1]-A[:,0]).mean():+.3f} ({(B[:,1]-B[:,0]).mean():+.3f})")
allg=min(GRID,key=lambda g:np.sqrt(np.mean(np.concatenate([(R[(o,g)][:,1]-R[(o,g)][:,0])**2 for o in SITES])))); print("best on all:",allg,{s:(round(rms(R[(s,allg)]),3),round(float((R[(s,allg)][:,1]-R[(s,allg)][:,0]).mean()),3)) for s in SITES})
# leave one year out
yrs=sorted({int(y) for s in SITES for y in R[(s,(0.0,0.0))][:,3]}); tot0=tot1=n=0
print("leave one year out (all sites): chosen K, delay | held-out rms vs baseline")
for yo in yrs:
    def sel(g,keep): 
        return np.concatenate([R[(o,g)][(R[(o,g)][:,3]!=yo)==keep] for o in SITES])
    g=min(GRID,key=lambda g:np.sqrt(np.mean((sel(g,True)[:,1]-sel(g,True)[:,0])**2)))
    A=sel(g,False); B=sel((0.0,0.0),False)
    if len(A): tot1+=((A[:,1]-A[:,0])**2).sum(); tot0+=((B[:,1]-B[:,0])**2).sum(); n+=len(A); print(f"  {yo}: K {g[1]:.1f} delay {g[0]:+.2f} | {rms(A):.3f} vs {rms(B):.3f}")
print(f" pooled held-out rms {math.sqrt(tot1/n):.3f} vs baseline {math.sqrt(tot0/n):.3f}")
json.dump({f"{s}|{g}":R[(s,g)].tolist() for s in SITES for g in GRID},open('/tmp/w/mead_lai_fit2.json','w'))
