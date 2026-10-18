"""Cycles' unstressed canopy law per crop (2026-10-18): fit Eq. 6 (plateau, a, b, c, d) to the binned median radiation interception of Cycles v1.5.20 on days with
nitrogen_stress and water_stress under 2 percent, versus TTf = thermal_time / MATURITY_TT.
Usage: CROPSEL=corn|silage|sorghum|soy CROPFILE=CornRM.90 MATTT=1800 NLEV=400 python3 canopy_shape_audit_2026_10_18.py"""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["N_LEVELS"]=os.environ.get("NLEV","400"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
from scipy.optimize import least_squares
CROPFILE=os.environ.get("CROPFILE","CornRM.90"); MATTT=float(os.environ.get("MATTT","1800")); NL=int(os.environ["N_LEVELS"])
S=json.load(open('sitesets/fresh94.json'))
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NL}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NL}/"
    rows=[r for r in csv.DictReader(open(d+f"daily{CROPFILE}.csv")) if r['date'][0]!='#' and r['thermal_time']!='-999']; shutil.rmtree(d,ignore_errors=True)
    out=[]
    for r in rows:
        try: tt=float(r['thermal_time'])/MATTT; e=float(r['radiation_interception']); ns=float(r['nitrogen_stress']); ws=float(r['water_stress'])
        except ValueError: continue
        if ns<2 and ws<2 and e>=0 and r['stage'] in ('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH','MATURITY'): out.append((tt,e))
    return out
if __name__=="__main__":
    ks=sorted(S)[::7][:14]
    with Pool(4) as p: R=p.map(one,ks)
    A=np.array([x for r in R for x in r]); A=A[(A[:,0]>0.02)&(A[:,0]<1.0)]
    xs=[];ys=[]
    for lo in np.arange(0.02,1.0,0.02):
        s=(A[:,0]>=lo)&(A[:,0]<lo+0.02)
        if s.sum()>30: xs.append(lo+0.01); ys.append(np.median(A[s,1]))
    xs=np.array(xs); ys=np.array(ys); f=lambda q,x=xs: q[0]/(1+np.exp(q[1]+q[2]*x)+np.exp(q[3]+q[4]*x))
    r=least_squares(lambda q:f(q)-ys,[0.95,6,-20,-15,16])
    pd=(1.0,6,-20,-15,16); en=(0.99,6,-20,-16,16)
    print(f"{os.environ.get('CROPSEL','corn')} {CROPFILE} N={NL}: unstressed days {len(A)}, bins {len(xs)}")
    print("fit  plateau %.3f a %.2f b %.2f c %.2f d %.2f   rms %.4f | engine shared (0.99,6,-20,-16,16) rms %.4f | paper default rms %.4f"%(*r.x,np.sqrt(np.mean((f(r.x)-ys)**2)),np.sqrt(np.mean((f(en)-ys)**2)),np.sqrt(np.mean((f(pd)-ys)**2))))
