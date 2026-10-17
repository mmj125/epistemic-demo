"""Designed N experiment for Cycles' wheat canopy (2026-10-17). Same site/weather, N = 0,30,60,90,150 (spring UAN, FALLN=60 starter when N>=60 as in the adopted wheat protocol),
so only N (hence N stress, and secondarily water via biomass) differs between runs. From Cycles' daily radiation_interception the stressed expansion clock is inverted with the documented
double-sigmoid (a,b)=(6,-20): xc=(ln(1/c-1)-a)/b on the expansion phase (c in 0.03..0.85, before senescence term matters), and its daily rate is compared with Cycles' own thermal-time
increment. rate ratio r=dxc/d(thermal_time) is normalised by its median on unstressed days, then regressed on Cycles' nitrogen_stress and water_stress (log-log) to recover the stress exponents
instead of the fitted nstress^3.25 and water^1.35. Usage: python3 wheat_designed_n_2026_10_17.py"""
import os,sys,json,csv,math,shutil,subprocess,numpy as np
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY; NS=(0,30,60,90,150)
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatD"; m.write_inputs(fs,lat,lon,wx,soil,cl); rows=[]
    for N in NS:
        W.FALLN=60.0 if N>=60 else 0.0
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
        c=open(f"{CY}/input/ContinuousCorn.ctrl").read().replace("ContinuousCorn.operation",f"{fs}N{N}.operation").replace("GenericHagerstown.soil",f"{fs}.soil").replace("RockSprings.weather",f"{fs}.weather"); open(f"{CY}/input/{fs}N{N}.ctrl","w").write(c)
        subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
        prev=None
        try:
            for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
                if x["date"][0]=="#" or x["biomass"]=="-999": prev=None; continue
                c=float(x["radiation_interception"]); tt=float(x["thermal_time"]); ns=1-float(x["nitrogen_stress"])/100; ws=1-float(x["water_stress"])/100
                if prev is not None and tt>prev[1]+0.5 and 0.03<prev[0]<0.85 and 0.03<c<0.85:
                    x0=(math.log(1/prev[0]-1)-6)/-20; x1=(math.log(1/c-1)-6)/-20
                    rows.append((N,ns,ws,(x1-x0)/(tt-prev[1]),tt,c))
                prev=(c,tt)
        finally: shutil.rmtree(d,ignore_errors=True)
    return rows
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:8]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    A=np.array([r for rr in R for r in rr]); np.save("/tmp/w/wheat_designed_n.npy",A); print("rows",len(A))
    N,ns,ws,r=A[:,0],A[:,1],A[:,2],A[:,3]
    ok=(ns>0.97)&(ws>0.97)&(r>0); r0=np.median(r[ok]); print("unstressed median rate %.3e (n=%d)"%(r0,ok.sum()))
    ok2=(r>0)&(ns>0.02)&(ws>0.02); y=np.log(r[ok2]/r0)
    X=np.c_[np.log(ns[ok2]),np.log(np.maximum(ws[ok2],1e-3))]; co,res,_,_=np.linalg.lstsq(X,y,rcond=None)
    pr=X@co; print("log-log fit: N-stress exponent %.2f, water exponent %.2f, R2 %.3f (n=%d)"%(co[0],co[1],1-((y-pr)**2).sum()/((y-y.mean())**2).sum(),ok2.sum()))
    for lo,hi in [(0.97,1.01),(0.8,0.97),(0.6,0.8),(0.4,0.6),(0.2,0.4),(0.02,0.2)]:
        s=(ok2)&(ns>=lo)&(ns<hi)&(ws>0.9)
        if s.sum()>20: print(f"  nstress {lo}-{hi}: n={s.sum()} median rate ratio {np.median(r[s]/r0):.2f}  (engine nstress^3.25 at mid: {((lo+hi)/2)**3.25:.2f})")
