"""Does the paper's hard-coded canopy curve (Eq. 6 with a,b,c,d = 6,-20,-15,16) describe Cycles v1.5.20's own radiation interception on unstressed days? (2026-10-18)
Binned by TTf = thermal_time / MATURITY_TT (1800 for CornRM.90), N=400 corn, days with nitrogen_stress and water_stress below 2 percent."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["N_LEVELS"]="400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json'))
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N400"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N400/"
    rows=[r for r in csv.DictReader(open(d+"dailyCornRM.90.csv")) if r['date'][0]!='#' and r['thermal_time']!='-999']; shutil.rmtree(d,ignore_errors=True)
    out=[]
    for r in rows:
        try: tt=float(r['thermal_time'])/1800.0; e=float(r['radiation_interception']); ns=float(r['nitrogen_stress']); ws=float(r['water_stress'])
        except ValueError: continue
        if ns<2 and ws<2 and e>=0: out.append((tt,e))
    return out
def eps(x,a,b,c,d): return 1.0/(1.0+np.exp(a+b*x)+np.exp(c+d*x))
if __name__=="__main__":
    ks=sorted(S)[::7][:14]
    with Pool(4) as p: R=p.map(one,ks)
    A=np.array([x for r in R for x in r]); print('unstressed days',len(A),'sites',len(ks))
    print(' TTf   Cycles median (p25-p75)   n  | paper default (6,-20,-15,16) | engine corn (6,-20,-5.35,4.1)')
    for lo in np.arange(0.0,1.35,0.1):
        s=(A[:,0]>=lo)&(A[:,0]<lo+0.1)
        if s.sum()>20:
            mid=lo+0.05; print(f" {mid:4.2f}   {np.median(A[s,1]):.3f} ({np.percentile(A[s,1],25):.3f}-{np.percentile(A[s,1],75):.3f})  {s.sum():5d} | {eps(mid,6,-20,-15,16):.3f} | {eps(mid,6,-20,-5.35,4.1):.3f}")
