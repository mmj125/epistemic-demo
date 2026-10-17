"""Wheat harvest index law variants at factor 1.0 (2026-10-16/17): 16 fresh sites, N=0 and 150, continuous winter wheat vs Cycles v1.5.20.
V0 current (thermal-time fraction, slope 1.0); V1 real f_G (post-anthesis growth share), slope 1.0; V2 real f_G, documented slope 2.5; V3 thermal-time fraction, slope 2.5."""
import os,sys,json,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
V={"V0":"","V1":"hi_use_thermal_time_fraction=False","V2":"hi_use_thermal_time_fraction=False;hi_slope=2.5","V3":"hi_slope=2.5"}
V.update(json.loads(os.environ.get("EXTRA","{}")))
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"; m.write_inputs(fs,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        open(f"{W.CY}/input/{fs}N{N}.operation","w").write(W.OP+(W.FERT%(N/0.32) if N>0 else ""))
        H=W.cycles_ref(fs,N)
        for k,ov in V.items():
            os.environ["CROPOVR"]=ov; R=W.engine_chain(wx,soil,cl,N,1.0)
            ys=[y for y in sorted(set(H)&set(R)) if y>1981]; x=[H[y]["grain"] for y in ys]; z=[R[y]["grain"] for y in ys]
            out[f"N{N}|{k}"]=dict(cg=st.mean(x),eg=st.mean(z),mae=st.mean(abs(i-j) for i,j in zip(x,z)),corr=W.corr(x,z),ehi=st.mean(R[y]["grain"]/R[y]["ag"] for y in ys if R[y]["ag"]>0),
                                  ct=st.mean(H[y]["total"] for y in ys),et=st.mean(R[y]["total"] for y in ys))
    return site,out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[int(os.environ.get("OFF","0"))::6][:16]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    json.dump(R,open(os.environ.get("OUT","/tmp/w/wheat_hi_test.json"),"w"))
    for N in (0,150):
        for k in V:
            g=lambda q:st.mean(o[f"N{N}|{k}"][q] for _,o in R); c=st.mean(o[f"N{N}|{k}"]["corr"] for _,o in R if o[f"N{N}|{k}"]["corr"]==o[f"N{N}|{k}"]["corr"])
            print(f"N={N} {k}: grain engine/Cycles {g('eg')/g('cg'):.3f}  yearly MAE {g('mae'):.3f} ({100*g('mae')/g('cg'):.0f}%)  within-site corr {c:.2f}  engine HI {g('ehi'):.3f}")
