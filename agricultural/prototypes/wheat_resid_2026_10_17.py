import os,sys,json,numpy as np
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E
from wheat_coupling_2026_10_17 import series, sub
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"; m.write_inputs(fs,lat,lon,wx,soil,cl); N=150
    open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+(W.FERT%(N/0.32)))
    F=series(fs,N); tgt={y:dict(d["canopy"]) for y,d in F.items()}
    E.FORCE_SERIES=sub(F,"KLN"); E.DIAG_STATE=[]; W.engine_chain(wx,soil,cl,N,1.0); D=E.DIAG_STATE; E.DIAG_STATE=None; E.FORCE_SERIES=None
    by={}
    for (y,doy,eie,ns,pn) in D:
        if y in tgt and doy in tgt[y]: by.setdefault(y,[]).append((doy,eie,tgt[y][doy]))
    out=[]
    for y,v in by.items():
        r=np.array([e-t for _,e,t in v]); out.append((site,y,float((r**2).mean()**.5),float(r.mean()),float(max(t for _,_,t in v)),float(max(e for _,e,_ in v)),len(v)))
    return out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:16]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    A=[x for rr in R for x in rr]; A=[x for x in A if x[6]>150]
    print("n site-years",len(A),"median rms %.3f"%np.median([x[2] for x in A]))
    print("by peak Cycles canopy: ")
    for lo,hi in ((0,0.3),(0.3,0.6),(0.6,0.8),(0.8,1.01)):
        b=[x for x in A if lo<=x[4]<hi]
        if b: print(f"  peak {lo}-{hi}: n={len(b)} mean rms {np.mean([x[2] for x in b]):.3f} mean bias {np.mean([x[3] for x in b]):+.3f} mean engine peak {np.mean([x[5] for x in b]):.2f} Cycles peak {np.mean([x[4] for x in b]):.2f}")
    print("worst:"); [print(" ",x[0],x[1],"rms %.3f bias %+.3f cyc peak %.2f eng peak %.2f"%x[2:6]) for x in sorted(A,key=lambda x:-x[2])[:8]]
