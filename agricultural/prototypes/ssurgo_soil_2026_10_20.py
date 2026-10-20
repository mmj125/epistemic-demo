"""Builds engine soil layers from SSURGO horizons (dominant component at the site point), keeping the STATSGO layer boundaries of the site (2026-10-20).
Per layer: depth-weighted clay, sand, organic C (om_r / 1.72), field capacity and wilting point as volumetric water (wthirdbar_r, wfifteenbar_r times bulk density), pH.
Input /tmp/w/ssurgo_horizons.json (SDA query, see ssurgo_fetch in the plan log); output sitesets/fresh94_ssurgo_soil.json."""
import json,sys
sys.path.insert(0,'.')
import numpy as np, field_data as fd
S=json.load(open('sitesets/fresh94.json')); H=json.load(open('/tmp/w/ssurgo_horizons.json')); out={}
def f(x): 
    try: return float(x)
    except Exception: return None
for s,(lat,lon) in sorted(S.items()):
    hz=H.get(s)
    if not hz: continue
    top=max(hz,key=lambda r:f(r["comppct_r"]) or 0)["cokey"]; hz=[r for r in hz if r["cokey"]==top]
    hz=[dict(z0=f(r["hzdept_r"])/100,z1=f(r["hzdepb_r"])/100,sand=f(r["sandtotal_r"]),clay=f(r["claytotal_r"]),om=f(r["om_r"]),bd=f(r["dbthirdbar_r"]),w33=f(r["wthirdbar_r"]),w15=f(r["wfifteenbar_r"]),ph=f(r["ph1to1h2o_r"])) for r in hz]
    hz=[h for h in hz if h["z0"] is not None and h["z1"] is not None and h["z1"]>h["z0"]]
    if not hz: continue
    soil,_,_=fd.resolve_field_soil(lat,lon); layers=[]; z=0.0
    for l in soil:
        a,b=z,z+l["thick"]; z=b; acc={k:[0.0,0.0] for k in ("sand","clay","om","bd","w33","w15","ph")}
        for h in hz:
            ov=max(0.0,min(b,h["z1"])-max(a,h["z0"]))
            for k in acc:
                if h[k] is not None and ov>0: acc[k][0]+=ov*h[k]; acc[k][1]+=ov
        if acc["clay"][1]==0:   # below the described profile: use the deepest horizon
            h=hz[-1]
            for k in acc:
                if h[k] is not None: acc[k]=[h[k],1.0]
        g=lambda k:(acc[k][0]/acc[k][1]) if acc[k][1]>0 else None
        bd,w33,w15=g("bd"),g("w33"),g("w15")
        d=dict(thick=l["thick"],clay=g("clay"),sand=g("sand"),soc=(g("om")/1.72 if g("om") is not None else l["soc"]),ph=g("ph"))
        if bd and w33 and w15: d["fc"]=w33*bd/100.0; d["pwp"]=w15*bd/100.0; d["bd"]=bd
        if d["clay"] is None: d["clay"],d["sand"]=l["clay"],l["sand"]
        layers.append(d)
    out[s]=layers
json.dump(out,open('sitesets/fresh94_ssurgo_soil.json','w')); print(len(out),"sites;",sum(1 for v in out.values() if all('fc' in l for l in v)),"with measured water retention in every layer")
