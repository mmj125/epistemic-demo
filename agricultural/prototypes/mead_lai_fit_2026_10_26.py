"""Canopy senescence timing against measured LAI at Mead (2026-10-26). Engine with tower-adjusted weather (temperature, humidity, wind from the tower), maize years only, BIF LAI dates (2001 to 2007) converted to intercepted fraction with
k = 0.55 (an assumption, tested 0.45 and 0.65), against the engine's canopy interception on the same dates. Grid over CANOPY_SENES_DELAY and CANOPY_SENES_STRESS_K; leave-one-site-out: parameters chosen on two sites, scored on the third.
Usage: python3 mead_lai_fit_2026_10_26.py"""
import os,sys,json,math
sys.path.insert(0,'.')
import numpy as np, mead_score_2026_10_23 as M, rhizo_engine as E
SITES=["Ne1","Ne2","Ne3"]; DATA={}
for s in SITES:
    soil,b,pl,lat,lon,wx,CW,CH,CYld,T=M._cache(s,"toweradj"); DATA[s]=(soil,pl,lat,wx,b,CH)
def obs_dates(s):
    soil,pl,lat,wx,b,CH=DATA[s]; out=[]
    for l in b["lai"]:
        d=l["LAI_DATE"]; iso=f"{d[:4]}-{d[4:6]}-{d[6:]}"; y=int(d[:4])
        if y in pl and pl[y]["crop"]=="corn": out.append((iso,float(l["LAI_TOT"]),int(d[4:6])))
    return out
def run(s,delay,k):
    soil,pl,lat,wx,b,CH=DATA[s]; E.CANOPY_SENES_DELAY=delay; E.CANOPY_SENES_STRESS_K=k
    try: res=M.engine_run(s,soil,pl,lat,wx)
    finally: E.CANOPY_SENES_DELAY=0.0; E.CANOPY_SENES_STRESS_K=0.0
    ED,_=M.engine_parse(res,soil); return ED
def score(s,ED,kext=0.55):
    rows=[]
    for iso,lai,mo in obs_dates(s):
        if iso in ED: rows.append((1-math.exp(-kext*lai),ED[iso]["fi"],mo,lai))
    return np.array(rows)
GRID=[(dl,k) for dl in (0.0,0.05,0.08,0.10,0.12,0.15,0.20) for k in (0.0,0.25,0.5,0.75,1.0,1.5)]
R={}
for s in SITES:
    for g in GRID: R[(s,g)]=score(s,run(s,*g))
    print(s,"n",len(R[(s,(0.0,0.0))]),flush=True)
def rms(A): return float(np.sqrt(((A[:,1]-A[:,0])**2).mean()))
print("baseline (documented shape) rms of intercepted fraction, bias by month (Jun Jul Aug Sep: model minus observed)")
for s in SITES:
    A=R[(s,(0.0,0.0))]; print(f" {s} rms {rms(A):.3f} n {len(A)} | "+" ".join(f"{m}:{(A[A[:,2]==m,1]-A[A[:,2]==m,0]).mean():+.2f}" for m in (6,7,8,9) if (A[:,2]==m).sum()>=2))
print("leave one site out: parameters minimising rms on the other two, score on the held-out site (baseline rms in brackets)")
tot0=tot1=0; n=0
for s in SITES:
    others=[o for o in SITES if o!=s]
    best=min(GRID,key=lambda g:np.sqrt(np.mean(np.concatenate([(R[(o,g)][:,1]-R[(o,g)][:,0])**2 for o in others]))))
    A=R[(s,best)]; B=R[(s,(0.0,0.0))]; print(f" held out {s}: chosen delay {best[0]:+.2f} K {best[1]:.0f}  rms {rms(A):.3f} ({rms(B):.3f})  Aug-Sep bias {(A[A[:,2]>=8,1]-A[A[:,2]>=8,0]).mean():+.2f} ({(B[B[:,2]>=8,1]-B[B[:,2]>=8,0]).mean():+.2f})")
allg=min(GRID,key=lambda g:np.sqrt(np.mean(np.concatenate([(R[(o,g)][:,1]-R[(o,g)][:,0])**2 for o in SITES]))))
print("best on all three:",allg,"rms",{s:round(rms(R[(s,allg)]),3) for s in SITES})
print("rms by grid (all sites pooled): rows delay, columns K 0 0.25 0.5 0.75 1 1.5")
for dl in (0.0,0.05,0.08,0.10,0.12,0.15,0.20):
    print(f" {dl:+.2f}",[round(float(np.sqrt(np.mean(np.concatenate([(R[(o,(dl,k))][:,1]-R[(o,(dl,k))][:,0])**2 for o in SITES])))),3) for k in (0.0,0.25,0.5,0.75,1.0,1.5)])
json.dump({f"{s}|{g}":R[(s,g)].tolist() for s in SITES for g in GRID},open('/tmp/w/mead_lai_fit.json','w'))

print("Aug-Sep only (n per site Ne1 14, Ne2 8, Ne3 9): bias of model interception minus observed, by site, at the best pooled setting and neighbours")
for g in (allg,(allg[0],0.0),(0.0,0.0)):
    print(g,{s:(round(float((R[(s,g)][R[(s,g)][:,2]>=8,1]-R[(s,g)][R[(s,g)][:,2]>=8,0]).mean()),3)) for s in SITES})
