"""Mead maize yield and above-ground biomass with planting days inferred from the early LAI (2026-10-26), for shoot partition TTf50 values. Planting before 2014 was assumed day 121; the inferred days (124 to 136) come from mead_lai_fit2.
Observed: BIF production (grain 'Fruits', 'Total' above-ground, gC m-2 / 0.438). Engine: tower-adjusted weather, current defaults (including the senescence law for corn). Usage: python3 mead_yield_plant_2026_10_26.py"""
import os,sys,json,math,copy,datetime
sys.path.insert(0,'.')
import numpy as np, mead_score_2026_10_23 as M, rhizo_engine as E
SH=[121,124,127,130,133,136,139,142]; C_FRAC=0.438; ROWS={}
for s in ("Ne1","Ne2","Ne3"):
    soil,b,pl,lat,lon,wx,CW,CH,CYld,T=M._cache(s,"toweradj"); obs={}
    for l in b["lai"]:
        d=l["LAI_DATE"]; iso=f"{d[:4]}-{d[4:6]}-{d[6:]}"; y=int(d[:4])
        if y in pl and pl[y]["crop"]=="corn" and not pl[y].get("documented_plant"): obs.setdefault(y,[]).append((iso,1-math.exp(-0.55*float(l["LAI_TOT"])),datetime.date.fromisoformat(iso).timetuple().tm_yday))
    runs={}
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
    prod={}
    for p in b["production"]:
        y=int(p["AG_PROD_DATE_START"][:4]); prod.setdefault(y,{})[p["AG_PROD_CROP_ORGAN"]]=float(p["AG_PROD_CROP"])/C_FRAC/100.0
    for t50 in (0.42,0.36,0.30,0.25):
        E.TTF50_SHOOT_PARTITION=t50; res=M.engine_run(s,soil,p3,lat,wx); ED,EY=M.engine_parse(res,soil)
        for y in sorted(best):
            if y in prod and y in EY: ROWS.setdefault((s,t50),[]).append((y,prod[y].get("Fruits",np.nan),EY[y]["grain"],prod[y].get("Total",np.nan),EY[y]["ag"]))
E.TTF50_SHOOT_PARTITION=0.42
print("site TTf50 | years | grain obs engine | above-ground total obs engine (Mg/ha, mean over the maize years with observations)")
for (s,t50),L in ROWS.items():
    A=np.array(L,float); print(f" {s} {t50:.2f} | {len(A)} | {np.nanmean(A[:,1]):.2f} {np.nanmean(A[:,2]):.2f} | {np.nanmean(A[:,3]):.2f} {np.nanmean(A[:,4]):.2f}")
for t50 in (0.42,0.36,0.30,0.25):
    A=np.vstack([np.array(ROWS[(s,t50)],float) for s in ("Ne1","Ne2","Ne3")]); k=~np.isnan(A[:,3]); g=~np.isnan(A[:,1])
    print(f" all sites TTf50 {t50:.2f}: above-ground engine/obs {A[k,4].mean()/A[k,3].mean():.3f} (n {k.sum()}) rms {np.sqrt(np.mean((A[k,4]-A[k,3])**2)):.2f} | grain engine/obs {A[g,2].mean()/A[g,1].mean():.3f} (n {g.sum()}) rms {np.sqrt(np.mean((A[g,2]-A[g,1])**2)):.2f}")

# observed above-ground biomass series (BIF 'Foliage', gC m-2) against the engine's daily above-ground biomass on the same dates, same inferred planting days
print("biomass through the season: month | n | observed, engine at TTf50 0.42, 0.30 (Mg/ha)")
for s in ("Ne1","Ne2","Ne3"):
    pass
BIO={}
for s in ("Ne1","Ne2","Ne3"):
    soil,b,pl,lat,lon,wx,CW,CH,CYld,T=M._cache(s,"toweradj")
    ob={}
    for x in b["biomass"]:
        if x["AG_BIOMASS_CROP_ORGAN"]=="Foliage":
            d=x["AG_BIOMASS_DATE"]; y=int(d[:4])
            if y in pl and pl[y]["crop"]=="corn" and not pl[y].get("documented_plant"): ob[f"{d[:4]}-{d[4:6]}-{d[6:]}"]=float(x["AG_BIOMASS_CROP"])/C_FRAC/100.0
    # reuse the inferred planting days by recomputing from the same LAI rule
    obs={}
    for l in b["lai"]:
        d=l["LAI_DATE"]; iso=f"{d[:4]}-{d[4:6]}-{d[6:]}"; y=int(d[:4])
        if y in pl and pl[y]["crop"]=="corn" and not pl[y].get("documented_plant"): obs.setdefault(y,[]).append((iso,1-math.exp(-0.55*float(l["LAI_TOT"])),datetime.date.fromisoformat(iso).timetuple().tm_yday))
    runs={}
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
    for t50 in (0.42,0.30):
        E.TTF50_SHOOT_PARTITION=t50; res=M.engine_run(s,soil,p3,lat,wx); ED,_=M.engine_parse(res,soil)
        for iso,v in ob.items():
            if iso in ED and int(iso[:4]) in best: BIO.setdefault((t50,int(iso[5:7])),[]).append((v,ED[iso]["ag"]))
E.TTF50_SHOOT_PARTITION=0.42
for mo in (6,7,8,9):
    a=np.array(BIO.get((0.42,mo),[]),float); c=np.array(BIO.get((0.30,mo),[]),float)
    if len(a)>=3: print(f" {mo} | {len(a)} | {a[:,0].mean():.2f} {a[:,1].mean():.2f} {c[:,1].mean():.2f}")
