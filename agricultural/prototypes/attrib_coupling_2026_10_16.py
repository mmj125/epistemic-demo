"""Canopy / nitrogen-stress coupling decomposition (2026-10-16). Splits the canopy clock into its N factor (nclock) and water factor (wclock), and the growth
multiplier (nstress), and forces Cycles' own daily values of each into the engine separately and in pairs. 24 fresh sites, corn, N=0 and 150, within-site yearly MAE.
K nclock (N factor on the canopy clock), L wclock (water factor on the clock), N nstress (growth multiplier), C canopy interception (overrides the clock result)."""
import os,sys,json,shutil,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, forcelib
from multiprocessing import Pool
CY=m.CY
KEYS={'K':'nclock','L':'wclock','N':'nstress','C':'canopy'}
MODES=['','K','L','KL','N','KN','LN','KLN','C','CN']
def sub(F,mode):
    ks=[KEYS[c] for c in mode]
    return {y:{k:(v if k in ks else {}) for k,v in d.items()} for y,d in F.items()}
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        H,A=m._run_cycles_uncached(site,N)
        F=forcelib.force(site,N,('wclock','canopy','water','nstress'))
        shutil.rmtree(f"{CY}/output/{site}N{N}",ignore_errors=True)
        for mode in MODES:
            E.FORCE_SERIES=sub(F,mode) if mode else None
            R=m.engine(site,wx,soil,cl,N,"leadin"); E.FORCE_SERIES=None
            ys=sorted(set(H)&set(R)); x=[H[y]["grain"] for y in ys]; z=[R[y]["grain"] for y in ys]
            out[f"N{N}|{mode or 'free'}"]=dict(mae=st.mean(abs(i-j) for i,j in zip(x,z)),bias=st.mean(j-i for i,j in zip(x,z)),mean=st.mean(x),corr=m.corr(x,z))
    return site,out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    json.dump(R,open("scorecards/2026-10-16_coupling_decomposition_24sites.json","w"))
    for N in (0,150):
        base=st.mean(o[f"N{N}|free"]["mae"] for _,o in R); ref=st.mean(o[f"N{N}|free"]["mean"] for _,o in R)
        for mode in MODES:
            k=f"N{N}|{mode or 'free'}"; mae=st.mean(o[k]["mae"] for _,o in R)
            c=st.mean(o[k]["corr"] for _,o in R if o[k]["corr"]==o[k]["corr"]); b=st.mean(o[k]["bias"] for _,o in R)
            print(f"N={N} {mode or 'free':5s} yearly MAE {mae:5.2f} ({100*mae/ref:3.0f}% of mean) removed {100*(base-mae)/base:+4.0f}%  bias {b:+.2f}  within-site corr {c:.2f}")
