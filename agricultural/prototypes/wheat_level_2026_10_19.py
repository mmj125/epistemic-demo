"""Wheat growth level with Cycles' daily canopy, water factor and N factor forced in (2026-10-19): engine over Cycles for total biomass and grain at harvest, 16 fresh sites, N=0 and 150, FALLN=60.
Corn, silage and sorghum read 1.002 to 1.007 above-ground at N>=150 in the same test (ngf 1.0). Uses wheat_attrib.series() for the forced series."""
import os,sys,json,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); os.environ["FALLN"]="60"; sys.path.insert(0,'.')
import wheat_attrib as A, run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatL"; out={}; m.write_inputs(fs,lat,lon,wx,soil,cl)
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N)); H=W.cycles_ref(fs,N); P=A.series(fs,N)
        for mode in ("free","all"):
            E.FORCE_SERIES=None if mode=="free" else {y:{k:v[k] for k in ("canopy","water","nstress")} for y,v in P.items()}
            R=W.engine_chain(wx,soil,cl,N,1.0); E.FORCE_SERIES=None
            ys=[y for y in sorted(set(H)&set(R)) if y>1981]
            out[f"N{N}|{mode}"]=dict(tot=(sum(R[y]["total"] for y in ys),sum(H[y]["total"] for y in ys)),grain=(sum(R[y]["grain"] for y in ys),sum(H[y]["grain"] for y in ys)))
    return site,out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:16]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    for N in (0,150):
        for mode in ("free","all"):
            t=[o[f"N{N}|{mode}"]["tot"] for _,o in R]; g=[o[f"N{N}|{mode}"]["grain"] for _,o in R]
            print(f"N={N} {mode:4s}: total biomass engine/Cycles {sum(a for a,b in t)/sum(b for a,b in t):.3f}   grain {sum(a for a,b in g)/sum(b for a,b in g):.3f}")
