"""Does the engine's departure from its earlier (Cycles-like residue) state move site-level county corn yields toward the observations? (2026-10-27)
Per site, mean yield over 2007 to 2016: observed (NASS county, corn N=150 comparator), Cycles, engine_old (ENG_OLD run file), engine_new (ENG_NEW run file).
Reports the share of sites where the new engine is closer to the observation than the old, the mean absolute site error of each, and the correlation between the move (new - old)
and the old error (observed - old). Usage: ENG_OLD=/tmp/w/cr_stoich.json ENG_NEW=/tmp/w/cr_all_wz.json python3 departure_test_2026_10_27.py"""
import json,os,sys,re
import numpy as np, pandas as pd
src=open('county_compare_2026_10_20.py').read()
head=src.split("def report(")[0]   # imports, data loading, cyc(), detrend(), stats()
head=head.replace("eng=json.load(open(os.environ.get('ENGRUN','/tmp/w/engine_county_runs.json')))","eng=json.load(open(os.environ['ENG_NEW']))")
ns={}; exec(head,ns)
old=json.load(open(os.environ['ENG_OLD']))
rows=ns['stats']("corn",ns['CROPS']["corn"])
res=[]
for r in rows:
    e_old={int(k):v for k,v in old[r["site"]]["corn"].items()}
    ev_old=np.array([e_old.get(y,np.nan) for y in r["yrs"]])
    m=(~np.isnan(ev_old))&(r["yrs"]>=2007)   # the level window of county_compare (the engine has no technology trend)
    if m.sum()<6: continue
    res.append(dict(site=r["site"],lon=r["lon"],o=r["o"][m].mean(),c=r["c"][m].mean(),old=ev_old[m].mean(),new=r["e"][m].mean()))
d=pd.DataFrame(res)
for label,sel in (("all",d.lon>-200),("east",d.lon>-97.5),("west",d.lon<=-97.5)):
    x=d[sel]
    err_old=(x.o-x.old); err_new=(x.o-x.new); move=x.new-x.old
    print(f"{label:5s} n={len(x):2d} obs {x.o.mean():.2f} Cycles {x.c.mean():.2f} old {x.old.mean():.2f} new {x.new.mean():.2f} | mean |site error| old {err_old.abs().mean():.2f} new {err_new.abs().mean():.2f} Cycles {(x.o-x.c).abs().mean():.2f} | new closer at {(err_new.abs()<err_old.abs()).mean()*100:.0f}% of sites | corr(move, old error) {np.corrcoef(move,err_old)[0,1]:+.2f}, slope {np.polyfit(err_old,move,1)[0]:+.2f}")
