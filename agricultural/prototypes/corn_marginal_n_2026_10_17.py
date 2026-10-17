"""Cycles' marginal total-N concentration of new growth, dTotalN/dTotalBiomass (%), by thermal-time fraction and by total biomass, for unstressed (N mult >= .97) and N-stressed days, corn 24 sites N=0,150,400 (2026-10-17), against the engine's n_marginal_demand_pct(W) x 0.7. Also the daily uptake split: days with growth vs days with no growth. Usage: python3 corn_marginal_n_2026_10_17.py"""
import os,sys,json,csv,shutil,subprocess
os.environ["N_LEVELS"]="0,150,400"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (0,150,400):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; prev=None
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999': prev=None; continue
            r=(float(x['biomass']),float(x['total_nitrogen']),float(x['thermal_time'])/1800.0,1-float(x['nitrogen_stress'])/100)
            if prev is not None: out.append((N,r[2],r[0],r[3],r[0]-prev[0],r[1]-prev[1],r[1]))
            prev=r
        shutil.rmtree(d,ignore_errors=True)
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    import numpy as np
    A=np.array(R); print("days",len(A)); crop=rv.CORN
    def mg(k): 
        db=A[k,4].sum(); return A[k,5].sum()/(db*10) if db>0 else float('nan')   # dN kg/ha / (dB Mg/ha*1000 kg) *100 %
    print("marginal total-N concentration of new growth (%) by thermal-time fraction")
    print("  ttf      unstressed(N>=.97)   N-stressed(<.9)    engine marginal at mean W (x1.0 / x0.7)")
    for lo in np.arange(0.1,1.0,0.1):
        ku=(A[:,1]>=lo)&(A[:,1]<lo+.1)&(A[:,3]>=.97)&(A[:,4]>0); ks=(A[:,1]>=lo)&(A[:,1]<lo+.1)&(A[:,3]<.9)&(A[:,4]>0)
        W=A[(A[:,1]>=lo)&(A[:,1]<lo+.1),2].mean(); em=E.n_marginal_demand_pct(W,crop)
        print(f"  {lo:.1f}   {mg(ku):6.2f} (n {ku.sum():6d})   {mg(ks):6.2f} (n {ks.sum():6d})    W {W:5.1f}: {em:.2f} / {0.7*em:.2f}")
    print("by total biomass, unstressed")
    for lo,hi in ((0.1,0.5),(0.5,1),(1,2),(2,4),(4,8),(8,12),(12,16),(16,20),(20,30)):
        k=(A[:,2]>=lo)&(A[:,2]<hi)&(A[:,3]>=.97)&(A[:,4]>0); W=A[k,2].mean() if k.sum() else 0
        if k.sum()>100: print(f"  W {lo}-{hi}: {mg(k):.2f}%  engine x0.7 {0.7*E.n_marginal_demand_pct(W,crop):.2f}% (n {k.sum()})")
