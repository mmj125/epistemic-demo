"""Does the engine's (and Cycles') county yield-level error trend with soil depth and available water capacity? Diagnostic only, nothing is fitted (2026-10-27).
Usage: ENGRUN=/tmp/w/cty_rc1.json python3 county_soil_regress_2026_10_27.py"""
import os,sys
src=open('county_compare_2026_10_20.py').read().split("\nfor crop,cfg in CROPS.items():")[0]
exec(src)
os.environ.setdefault("REGIONAL","0")
import run_validation_multisite as m
S=json.load(open('sitesets/fresh94.json')); feat={}
for s,(lat,lon) in S.items():
    soil,_,_=m.fd.resolve_field_soil(lat,lon); th=sum(l['thick'] for l in soil); h=[m.saxton_rawls(l['sand'],l['clay'],l['soc']*1.72) for l in soil]
    w=np.array([l['thick'] for l in soil])/th
    feat[s]=[th,sum((x['fc']-x['pwp'])*l['thick'] for x,l in zip(h,soil))*1000,float(sum(w*[l['sand'] for l in soil])),float(sum(w*[l['clay'] for l in soil]))]
rows=stats("corn",CROPS["corn"]); names=('depth','awc','sand','clay')
E_,C_,F=[],[],[]
for r in rows:
    sel=r["yrs"]>=2007
    if not sel.any(): continue
    o=r["o"][sel].mean(); E_.append(r["e"][sel].mean()/o); C_.append(r["c"][sel].mean()/o); F.append(feat[r["site"]])
E_,C_,F=np.array(E_),np.array(C_),np.array(F)
print(f"{len(E_)} sites; level vs county: engine x{np.median(E_):.2f}, Cycles x{np.median(C_):.2f}")
for lab,y in (("engine/county",E_),("Cycles/county",C_),("engine/Cycles",E_/C_)):
    print(f"  {lab:14s}"," ".join(f"{n}: r={np.corrcoef(F[:,i],y)[0,1]:+.2f}" for i,n in enumerate(names)))
q=np.percentile(F[:,1],[25,75])
for lab,y in (("engine",E_),("Cycles",C_)):
    print(f"  {lab} level, lowest AWC quartile x{np.median(y[F[:,1]<q[0]]):.2f}, highest x{np.median(y[F[:,1]>q[1]]):.2f}")
