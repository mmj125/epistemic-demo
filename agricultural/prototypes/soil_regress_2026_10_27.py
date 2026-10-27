"""Regress the engine-minus-Cycles biomass and grain error on soil texture, depth and available water capacity across the 94 sites (2026-10-27). Usage: python3 soil_regress_2026_10_27.py TAG (e.g. rc1_corn)"""
import os,sys,json,glob
os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
tag=sys.argv[1]; D={}
for f in glob.glob(f"/tmp/w/{tag}_[0-3].json"): D.update(json.load(open(f)))
S=json.load(open('sitesets/fresh94.json')); feat={}
for s,(lat,lon) in S.items():
    soil,_,_=m.fd.resolve_field_soil(lat,lon); th=sum(l['thick'] for l in soil)
    h=[m.saxton_rawls(l['sand'],l['clay'],l['soc']*1.72) for l in soil]
    awc=sum((x['fc']-x['pwp'])*l['thick'] for x,l in zip(h,soil))*1000
    w=np.array([l['thick'] for l in soil])/th
    feat[s]=dict(sand=float(sum(w*[l['sand'] for l in soil])),clay=float(sum(w*[l['clay'] for l in soil])),depth=th,awc=awc,lat=lat)
for n in (150,400):
    rows=[]
    for k,v in D.items():
        p=k.split('|')
        if f"|N{n}|" not in k: continue
        site=p[0]
        if site not in feat: continue
        g=np.array(v["res"]["grain"]["pairs"]); b=np.array(v["res"]["total_biomass"]["pairs"])
        rows.append((site,g[:,1].mean()/g[:,0].mean()-1,b[:,1].mean()/b[:,0].mean()-1,g[:,0].mean()))
    if not rows: print("no rows for",n,list(D)[:2]); continue
    X=np.array([[feat[r[0]][c] for c in ('sand','clay','depth','awc','lat')] for r in rows]); 
    print(f"N={n}: {len(rows)} sites; mean grain error {np.mean([r[1] for r in rows]):+.3f}, sd {np.std([r[1] for r in rows]):.3f}")
    for lab,idx in (("grain",1),("biomass",2)):
        y=np.array([r[idx] for r in rows])
        out=[f"{c}: r={np.corrcoef(X[:,i],y)[0,1]:+.2f}" for i,c in enumerate(('sand','clay','depth','awc','lat'))]
        A=np.c_[np.ones(len(y)),(X-X.mean(0))/X.std(0)]; beta=np.linalg.lstsq(A,y,rcond=None)[0]; r2=1-((y-A@beta)**2).sum()/((y-y.mean())**2).sum()
        print(f"  {lab}: "," ".join(out),f"| multi R2 {r2:.2f}")
    lo=[r[1] for r in rows if feat[r[0]]['awc']<np.percentile([feat[x[0]]['awc'] for x in rows],25)]; hi=[r[1] for r in rows if feat[r[0]]['awc']>np.percentile([feat[x[0]]['awc'] for x in rows],75)]
    print(f"  grain error lowest AWC quartile {np.mean(lo):+.3f}, highest {np.mean(hi):+.3f}")
