"""Corn mass components (2026-10-17): aboveground biomass, root biomass and grain at harvest, engine vs Cycles v1.5.20, free and with all Cycles states forced (canopy, water, N stress, clocks, net mineralization, mineral pool), 47 fresh sites (every second), N=0/150/400, continuous chain. Reports mean ratios engine/Cycles and AG harvest index by N and latitude band. Usage: ENGINE_OVR=... python3 corn_components_2026_10_17.py"""
import os,sys,json,shutil,subprocess,statistics as st
os.environ["N_LEVELS"]="0,150,400"; os.environ.setdefault("REGIONAL","0"); os.environ.setdefault("LEAD_YEARS","continuous"); os.environ.setdefault("YEAR_STEP","2"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, forcelib
from mask_attrib_2026_10_16 import harv
from multiprocessing import Pool
CY=m.CY; ALL=("canopy","water","wclock","nstress","nclock","netmin","minn")
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (0,150,400):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"
        H=harv(d); F=forcelib.force(site,N,("wclock","canopy","water","nstress","netmin","minn")); shutil.rmtree(d,ignore_errors=True)
        for mode in ("free","all"):
            E.FORCE_SERIES=None if mode=="free" else {y:{k:v[k] for k in ALL if k in v} for y,v in F.items()}
            R=m.engine(site,wx,soil,cl,N,"leadin"); E.FORCE_SERIES=None
            for y in sorted(set(H)&set(R)):
                h=H[y]
                if h["hi"]<=0.05: continue
                cag=h["grain"]/h["hi"]; out.append((site,lat,N,mode,cag,h["total"]-cag,h["grain"],R[y]["ag"],R[y]["total"]-R[y]["ag"],R[y]["grain"]))
    return out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::2]
    with Pool(4) as p: R=sum(p.map(one,[(k,S[k]) for k in ks]),[])
    json.dump(R,open("/tmp/w/components.json","w"))
    import numpy as np
    A=np.array([[r[1],r[2],1 if r[3]=="all" else 0]+list(r[4:]) for r in R])
    for mode in (0,1):
        print("ALL STATES FORCED" if mode else "FREE")
        for N in (0,150,400):
            for lo,hi in ((25,35),(35,45),(45,50),(25,50)):
                k=(A[:,2]==mode)&(A[:,1]==N)&(A[:,0]>=lo)&(A[:,0]<hi)
                if k.sum()==0: continue
                a=A[k]; cag,croot,cg,eag,eroot,eg=[a[:,i].mean() for i in range(3,9)]
                print(f" N={N:3d} {lo}-{hi}N n={k.sum():4d}: AG E/C {eag/cag:.3f} ({eag:.1f}/{cag:.1f})  root E/C {eroot/croot:.3f} ({eroot:.2f}/{croot:.2f})  grain E/C {eg/cg:.3f}  HI(AG) C {cg/cag:.3f} E {eg/eag:.3f}")
