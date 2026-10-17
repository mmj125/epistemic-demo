"""Wheat canopy clock exponents scanned with Cycles' stress forced (2026-10-17): daily canopy rms vs Cycles interception for CANOPY_N_POW x CANOPY_WATER_POW (and eix 0.86 as in the engine's wheat crop dict).
16 fresh sites (OFF env), N=0 and 150, nclock/wclock/nstress forced, canopy left to the engine."""
import os,sys,json,itertools,numpy as np
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E
from wheat_coupling_2026_10_17 import series, sub
from multiprocessing import Pool
CY=m.CY
GRID=[(n,w) for n in (3.25,2.0,1.25,0.75) for w in (1.35,0.8)]
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"; m.write_inputs(fs,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+(W.FERT%(N/0.32) if N>0 else ""))
        F=series(fs,N); tgt={y:dict(d["canopy"]) for y,d in F.items()}
        for (np_,wp) in GRID:
            E.CANOPY_N_POW=np_; E.CANOPY_WATER_POW=wp; E.FORCE_SERIES=sub(F,"KLN"); E.DIAG_STATE=[]
            W.engine_chain(wx,soil,cl,N,1.0); D=E.DIAG_STATE; E.DIAG_STATE=None; E.FORCE_SERIES=None
            r=[eie-tgt[y][doy] for (y,doy,eie,ns,pn) in D if y in tgt and doy in tgt[y]]
            out[f"{N}|{np_}|{wp}"]=(float(np.sum(np.square(r))),len(r),float(np.sum(r)))
        E.CANOPY_N_POW=3.25; E.CANOPY_WATER_POW=1.35
    return out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[int(os.environ.get("OFF","0"))::6][:16]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    for N in (0,150):
        for (n,w) in GRID:
            k=f"{N}|{n}|{w}"; ss=sum(o[k][0] for o in R); c=sum(o[k][1] for o in R); b=sum(o[k][2] for o in R)/c
            print(f"N={N} N_POW {n:4} W_POW {w:4}  canopy rms {(ss/c)**.5:.4f} bias {b:+.4f}")
