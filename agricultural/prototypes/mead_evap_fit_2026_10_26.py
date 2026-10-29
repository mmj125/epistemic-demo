"""Soil evaporation law against Mead tower evapotranspiration (2026-10-26). Canopy-free days only (engine interception below 0.15): spring (day 90 to 139) and autumn (day 275 to 330), tower ET (LE) against the engine's soil plus residue evaporation, tower-adjusted weather with the tower's rain,
three sites (irrigated sites 2014 to 2016 only, Ne3 2001 to 2016). Grid over EVAP_LAW_PARAMS (air dry fraction, critical fraction of field capacity, exponent); leave one site out. Usage: python3 mead_evap_fit_2026_10_26.py"""
import os,sys,json,math
sys.path.insert(0,'.')
import numpy as np, mead_score_2026_10_23 as M, rhizo_engine as E
SITES=["Ne1","Ne2","Ne3"]; DATA={}
for s in SITES:
    soil,b,pl,lat,lon,wx0,CW,CH,CYld,T=M._cache(s,"toweradj"); T2,_=M.tower(s)
    wx=M.tower_rain_weather(wx0,T2); DATA[s]=(soil,pl,lat,wx,T2)
def days(ED,T,s):
    out=[]
    for d,v in ED.items():
        y=int(d[:4]); doy=M.dt.date.fromisoformat(d).timetuple().tm_yday
        if y in M.score_years(s) and d in T and not np.isnan(T[d]["et"]) and v["fi"]<0.15 and (90<=doy<=139 or 275<=doy<=330): out.append((T[d]["et"],v["et"],doy<200))
    return np.array(out,float)
GRID=[(0.5,b,n,z) for b in (0.85,1.0,1.25,1.5) for n in (3.5,6.0,12.0) for z in (0.05,0.1,0.2)]
R={}
for s in SITES:
    soil,pl,lat,wx,T=DATA[s]
    for g in GRID+[(0.25,0.85,3.5,0.2)]:
        E.EVAP_LAW_PARAMS=g[:3]; E.EVAP_ZONE_DEPTH_M=g[3]
        try: res=M.engine_run(s,soil,pl,lat,wx)
        finally: E.EVAP_LAW_PARAMS=(0.25,0.85,3.5); E.EVAP_ZONE_DEPTH_M=0.2
        ED,_=M.engine_parse(res,soil); R[(s,g)]=days(ED,T,s)
def stat(A): return (float(A[:,0].mean()),float(A[:,1].mean()),float(np.sqrt(np.mean((A[:,1]-A[:,0])**2))))
cur=(0.25,0.85,3.5,0.2)
print("current default (0.25, 0.85, 3.5, 0.2) mean tower ET, engine ET, rms (mm/day), n:",{s:(tuple(round(x,2) for x in stat(R[(s,cur)]))+(len(R[(s,cur)]),)) for s in SITES})
pool=lambda g,ss:float(np.sqrt(np.mean(np.concatenate([(R[(o,g)][:,1]-R[(o,g)][:,0])**2 for o in ss]))))
best=min(GRID,key=lambda g:pool(g,SITES)); print("best pooled",best,round(pool(best,SITES),3),"current",round(float(np.sqrt(np.mean(np.concatenate([(R[(o,cur)][:,1]-R[(o,cur)][:,0])**2 for o in SITES])))),3))
for s in SITES:
    others=[o for o in SITES if o!=s]; g=min(GRID,key=lambda g:pool(g,others)); A=R[(s,g)]; B=R[(s,cur)]
    print(f" held out {s}: chosen {g} | rms {stat(A)[2]:.2f} bias {stat(A)[1]-stat(A)[0]:+.2f} (current {stat(B)[2]:.2f}, {stat(B)[1]-stat(B)[0]:+.2f})")
print("rms by (b, n, zone depth) pooled: rows b n, columns depth 0.05 0.1 0.2")
for b in (0.85,1.0,1.25,1.5):
    for n in (3.5,6.0,12.0): print(f" b {b} n {n}",[round(pool((0.5,b,n,z),SITES),2) for z in (0.05,0.1,0.2)])
print("best pooled:",best,{s:tuple(round(x,2) for x in stat(R[(s,best)])) for s in SITES})
