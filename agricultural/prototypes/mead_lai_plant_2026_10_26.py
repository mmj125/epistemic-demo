"""Is the 'senescence is early at the irrigated Mead sites' result a planting date artifact? (2026-10-26) Planting days before 2014 are assumed (day 121). For each site-year with LAI observations, the planting day (121 to 142) that best matches the LAI observed before day 195 (expansion only, k 0.55) is chosen,
then the senescence-period (Aug and Sep) bias is read from the same run. Engine with tower-adjusted weather, documented shape (delay 0, K 0). Usage: python3 mead_lai_plant_2026_10_26.py"""
import os,sys,json,math,copy,datetime
sys.path.insert(0,'.')
import numpy as np, mead_score_2026_10_23 as M, rhizo_engine as E
SITES=["Ne1","Ne2","Ne3"]; SH=[121,124,127,130,133,136,139,142]; out={}
for s in SITES:
    soil,b,pl,lat,lon,wx,CW,CH,CYld,T=M._cache(s,"toweradj"); runs={}
    for sh in SH:
        p2=copy.deepcopy(pl)
        for y,v in p2.items():
            if v["crop"]=="corn" and not v.get("documented_plant"): v["plant"]=sh
        res=M.engine_run(s,soil,p2,lat,wx); ED,_=M.engine_parse(res,soil); runs[sh]=ED
    obs={}
    for l in b["lai"]:
        d=l["LAI_DATE"]; iso=f"{d[:4]}-{d[4:6]}-{d[6:]}"; y=int(d[:4])
        if y in pl and pl[y]["crop"]=="corn" and not pl[y].get("documented_plant"): obs.setdefault(y,[]).append((iso,1-math.exp(-0.55*float(l["LAI_TOT"])),datetime.date.fromisoformat(iso).timetuple().tm_yday,int(d[4:6])))
    rows=[]
    for y,L in sorted(obs.items()):
        early=[x for x in L if x[2]<195]
        if len(early)<3: continue
        err={sh:np.sqrt(np.mean([(runs[sh][x[0]]["fi"]-x[1])**2 for x in early if x[0] in runs[sh]])) for sh in SH}
        best=min(err,key=err.get); late=[x for x in L if x[3]>=8 and x[0] in runs[best] and x[0] in runs[121]]
        lb=np.mean([runs[best][x[0]]["fi"]-x[1] for x in late]) if late else np.nan; l121=np.mean([runs[121][x[0]]["fi"]-x[1] for x in late]) if late else np.nan
        rows.append((y,best,err[best],err[121],lb,l121,len(late)))
    out[s]=rows
    print(s,"year | best planting day | early rms best / day 121 | Aug-Sep bias (model minus observed) at best day / at day 121 | n late")
    for r in rows: print(f"  {r[0]} {r[1]:4d} | {r[2]:.3f} {r[3]:.3f} | {r[4]:+.3f} {r[5]:+.3f} | {r[6]}")
    A=np.array(rows,float); k=~np.isnan(A[:,4]); print(f"  {s} mean best day {A[:,1].mean():.0f}; mean Aug-Sep bias at best day {np.nanmean(A[k,4]):+.3f} against {np.nanmean(A[k,5]):+.3f} at day 121")
