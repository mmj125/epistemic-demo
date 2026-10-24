"""Grain-error attribution on the current engine (2026-10-16): force Cycles' own daily states into the engine and read the remaining grain error.
24 fresh sites (/tmp/w/s24.json), corn, N=0 and 150, 37 years. C canopy interception, W water stress + stress clocks, N nitrogen stress, M net mineralization (growing season).
Reports within-site yearly MAE, bias and correlation per mode, and the share of the free-run MAE removed."""
import os,sys,json,shutil,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, rhizo_engine as E, forcelib
from multiprocessing import Pool
CY=m.CY
BLK={'C':('canopy',),'W':('water','wclock'),'N':('nstress',),'M':('netmin',)}
MODES=['','C','W','N','M','CW','CN','CWN','CWNM']
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        H,A=m._run_cycles_uncached(site,N)
        Fs={mode:(forcelib.force(site,N,tuple(k for b in mode for k in BLK[b])) if mode else None) for mode in MODES}
        shutil.rmtree(f"{CY}/output/{site}N{N}",ignore_errors=True)
        for mode in MODES:
            E.FORCE_SERIES=Fs[mode]
            R=m.engine(site,wx,soil,cl,N,"leadin"); E.FORCE_SERIES=None
            ys=[y for y in sorted(set(H)&set(R))]
            x=[H[y]["grain"] for y in ys]; z=[R[y]["grain"] for y in ys]
            out[f"N{N}|{mode or 'free'}"]=dict(mae=st.mean(abs(i-j) for i,j in zip(x,z)),bias=st.mean(j-i for i,j in zip(x,z)),mean=st.mean(x),corr=m.corr(x,z))
    return site,out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    json.dump(R,open("scorecards/2026-10-16_attribution_current_engine.json","w"))
    for N in (0,150):
        base=st.mean(o[f"N{N}|free"]["mae"] for _,o in R); ref=st.mean(o[f"N{N}|free"]["mean"] for _,o in R)
        for mode in MODES:
            k=f"N{N}|{mode or 'free'}"; mae=st.mean(o[k]["mae"] for _,o in R)
            c=st.mean(o[k]["corr"] for _,o in R if o[k]["corr"]==o[k]["corr"]); b=st.mean(o[k]["bias"] for _,o in R)
            print(f"N={N} {mode or 'free':5s} yearly MAE {mae:5.2f} ({100*mae/ref:3.0f}% of mean) removed {100*(base-mae)/base:+4.0f}%  bias {b:+.2f}  within-site corr {c:.2f}")
