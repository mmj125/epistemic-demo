"""Grain and straw N in Cycles (2026-10-16), what a grain/straw N pool would have to reproduce: 24 fresh sites, corn, N=0 and 150. From harvest.csv: grain N, residue N, nitrogen harvest index (grain N / total plant N),
grain and residue N concentrations, implied residue C:N (45% C of dry matter), and the spread across years and sites. Compared with the engine's fixed STAND/FLAT residue C:N of 86 (soilLayersCN medians)."""
import os,sys,json,csv,shutil,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        m._run_cycles_uncached(site,N); d=f"{CY}/output/{site}N{N}/"; rows=[]
        for x in csv.DictReader(open(d+"harvest.csv")):
            if x["date"][0]=="#": continue
            g=float(x["grain_yield"]); res=float(x["aboveground_residue"]); gn=float(x["grain_nitrogen"]); rn=float(x["nitrogen_in_residue"]); tn=float(x["total_nitrogen"]); rt=float(x["root_nitrogen"])
            if g>0.05 and res>0.1 and tn>0: rows.append(dict(nhi=gn/(tn),gconc=gn/g,rconc=rn/res,cn=450.0/(rn/res),agshare=(gn+rn)/tn,tn=tn))
        shutil.rmtree(d,ignore_errors=True)
        if not rows: out[N]=None; continue
        out[N]={k:st.mean(r[k] for r in rows) for k in rows[0]}|{"cn_sd":st.pstdev([r["cn"] for r in rows]),"n":len(rows)}
    return site,out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    json.dump(R,open("scorecards/2026-10-16_grain_straw_n_cycles_24sites.json","w"))
    for N in (0,150):
        RR=[(s,o) for s,o in R if o[N]]; g=lambda k:st.mean(o[N][k] for _,o in RR); sd=lambda k:st.pstdev([o[N][k] for _,o in RR])
        print(f"N={N}: N harvest index {g('nhi'):.2f} (site sd {sd('nhi'):.2f}); grain N conc {g('gconc'):.1f} kg/Mg (sd {sd('gconc'):.1f}); residue N conc {g('rconc'):.2f} kg/Mg (sd {sd('rconc'):.2f}); implied residue C:N {g('cn'):.0f} (site sd {sd('cn'):.0f}, within-site sd {g('cn_sd'):.0f}); aboveground share of plant N {g('agshare'):.2f}; plant N {g('tn'):.0f}")
