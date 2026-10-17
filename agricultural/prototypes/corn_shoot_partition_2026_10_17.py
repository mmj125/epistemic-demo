"""Marginal shoot fraction of new growth (daily dAG/dTotal) versus thermal-time fraction in Cycles v1.5.20 corn output, 24 sites x N=0,150 (2026-10-17), binned, against the engine's Michaelis-Menten form fsti + (fstf-fsti)/(1+(ttf50/ttf)^4) with fsti .45, fstf .95, ttf50 .32. Also the best exponent/ttf50 pair fitted over bins. Usage: python3 corn_shoot_partition_2026_10_17.py"""
import os,sys,json,csv,shutil,subprocess,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (0,150):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; prev=None
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999': prev=None; continue
            r=(float(x['thermal_time']),float(x['biomass']),float(x['aboveground_biomass']))
            if prev and r[0]>prev[0]:
                dt=r[1]-prev[1]; da=r[2]-prev[2]
                if dt>0.05: out.append((r[0]/1800.0,da/dt))
            prev=r
        shutil.rmtree(d,ignore_errors=True)
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    import numpy as np
    json.dump(R,open("/tmp/w/shoot_part.json","w"))
    A=np.array(R); f=lambda t,e,t50:0.45+0.5/(1+(t50/np.maximum(t,1e-6))**e)
    print("ttf bin: n  Cycles median marginal shoot fraction | engine form (e=4, ttf50=.32)")
    for lo in np.arange(0.0,1.0,0.1):
        k=(A[:,0]>=lo)&(A[:,0]<lo+0.1)
        if k.sum()>30: print(f" {lo:.1f}-{lo+.1:.1f}: {k.sum():6d}  {np.median(A[k,1]):.3f} (mean {A[k,1].mean():.3f}) | {f(lo+.05,4,0.32):.3f}")
    from scipy.optimize import least_squares
    k=(A[:,0]>0.03)&(A[:,0]<1.0)&(A[:,1]>0)&(A[:,1]<1.2)
    for e0 in (2,4,6):
        r=least_squares(lambda p:f(A[k,0],p[0],p[1])-A[k,1],[e0,0.32],loss='soft_l1'); print("fit exponent %.2f ttf50 %.3f rms %.4f"%(r.x[0],r.x[1],np.sqrt(np.mean((f(A[k,0],*r.x)-A[k,1])**2))))
    print("current form rms %.4f"%np.sqrt(np.mean((f(A[k,0],4,0.32)-A[k,1])**2)))
