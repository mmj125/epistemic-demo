"""Fit wheat's canopy shape (a,b,c,d) and plateau eix from Cycles' daily interception given the engine's own two clocks (2026-10-17).
Cycles' daily nclock/wclock/nstress are forced into the engine so the engine clock xc and development clock xt are what Cycles' stress implies; every canopy_cover_two call is logged with the day,
then (a,b,c,d,eix) is fit by least squares to Cycles' radiation_interception. 16 fresh sites (OFF=0), N=0 and 150. Usage: python3 wheat_canopy_fit_2026_10_17.py"""
import os,sys,json,csv,datetime,shutil,subprocess,numpy as np
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E
from wheat_coupling_2026_10_17 import series, sub
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"; m.write_inputs(fs,lat,lon,wx,soil,cl); rows=[]
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+(W.FERT%(N/0.32) if N>0 else ""))
        F=series(fs,N); tgt={y:dict(d["canopy"]) for y,d in F.items()}
        E.FORCE_SERIES=sub(F,"KLN"); E.DIAG_STATE=[]; log=[]; _o=E.canopy_cover_two
        E.canopy_cover_two=lambda xc,xt,eix=1.0,shape=None,_o=_o:(log.append((xc,xt)),_o(xc,xt,eix,shape) if shape is not None else _o(xc,xt,eix))[1]
        W.engine_chain(wx,soil,cl,N,1.0); D=E.DIAG_STATE; E.DIAG_STATE=None; E.FORCE_SERIES=None; E.canopy_cover_two=_o
        if len(D)!=len(log): continue
        for (y,doy,eie,ns,pn),(xc,xt) in zip(D,log):
            t=tgt.get(y,{}).get(doy)
            if t is not None: rows.append((xc,xt,t,N,doy))
    return rows
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[int(os.environ.get("OFF","0"))::6][:16]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    A=np.array([r for rr in R for r in rr]); print("rows",len(A)); np.save("/tmp/w/wheat_canopy_rows.npy",A)
    xc,xt,t=A[:,0],A[:,1],A[:,2]
    def pred(p,xc=xc,xt=xt): a,b,c,d,e=p; return e/(1+np.exp(a+b*np.maximum(0,xc))+np.exp(c+d*np.maximum(0,xt)))
    from scipy.optimize import least_squares
    p0=[6,-20,-15,16,0.99]; r0=pred(p0)-t; print("current  rms %.4f bias %+.4f"%((r0**2).mean()**.5,r0.mean()))
    best=None
    for s in ([6,-20,-15,16,.9],[4,-12,-8,8,.86],[5,-15,-12,12,.86],[3,-10,-6,6,.9]):
        f=least_squares(lambda p:pred(p)-t,s,max_nfev=3000)
        if best is None or f.cost<best.cost: best=f
    p=best.x; r=pred(p)-t; print("fit a,b,c,d,eix =",np.round(p,3),"rms %.4f bias %+.4f"%((r**2).mean()**.5,r.mean()))
    json.dump(list(map(float,p)),open("/tmp/w/wheat_canopy_fit.json","w"))
