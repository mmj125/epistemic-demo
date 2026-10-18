"""Cycles' supply-limited N uptake law (2026-10-18). Corn N=0, 24 sites, Cycles output only. Per growing day: uptake = positive change in total_nitrogen; mineral pool = NO3+NH4 (profile, previous day); nitrate;
transpiration (mm); profile soil water (mm, from layer moisture x thickness); N stress. Supply-limited days = N stress > 30 percent. Tests candidate forms on those days."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    C=rd(d+"dailyCornRM.90.csv"); Nn={r['date']:r for r in rd(d+"dailyN.csv")}; W={r['date']:r for r in rd(d+"dailyWater.csv")}; shutil.rmtree(d,ignore_errors=True)
    thick=[l['thick'] for l in soil]; rows=[]; prev=None; prevd=None
    for r in C:
        if r['total_nitrogen']=='-999': prev=None; continue
        tn=float(r['total_nitrogen'])
        if prev is not None and prevd in Nn and r['date'] in W:
            n0=Nn[prevd]; w=W[r['date']]
            nl=[k for k in w if k.startswith('soil_moisture_content.')]
            pw=sum(float(w[k])*1000*t for k,t in zip(sorted(nl,key=lambda x:int(x.split('.')[1])),thick))
            rows.append((tn-prev,float(n0['profile_soil_NO3'])+float(n0['profile_soil_NH4']),float(n0['profile_soil_NO3']),float(w['transpiration']),pw,float(r['nitrogen_stress']),float(r['biomass']),float(r['water_stress'])))
        prev=tn; prevd=r['date']
    return np.array(rows)
if __name__=="__main__":
    A=np.vstack([a for a in Pool(4).map(one,sorted(S)) if len(a)]); np.save('/tmp/w/nuptake_law.npy',A)
    U,P,NO3,T,PW,ns,B,ws=A.T; sel=(ns>30)&(U>0)&(P>1)&(T>0.05)
    print('supply-limited days',sel.sum(),'of',len(A))
    u,p,n3,t,pw=U[sel],P[sel],NO3[sel],T[sel],PW[sel]
    print('median uptake %.3f kg/ha/d, pool %.1f, nitrate %.1f, T %.2f mm, soil water %.0f mm'%(np.median(u),np.median(p),np.median(n3),np.median(t),np.median(pw)))
    for lab,x in (('pool',p),('pool*T/PW (mass flow of mineral N)',p*t/pw),('nitrate*T/PW',n3*t/pw),('pool*T',p*t),('T',t),('pool*sqrt(T)',p*np.sqrt(t))):
        c=np.corrcoef(u,x)[0,1]; k=(u*x).sum()/(x*x).sum(); r=np.sqrt(np.mean((u-k*x)**2))
        print(f'  uptake vs {lab:36s} corr {c:+.3f}  best k {k:9.4f}  rms {r:.3f}')
    print('uptake / pool by T bin (mm):')
    for lo,hi in ((0,.5),(.5,1),(1,2),(2,3),(3,4),(4,6),(6,12)):
        s=(t>=lo)&(t<hi)
        if s.sum()>200: print(f'   T {lo:3.1f}-{hi:4.1f}: n {s.sum():6d} U/pool median {np.median(u[s]/p[s]):.3f} p90 {np.percentile(u[s]/p[s],90):.3f}  U median {np.median(u[s]):.3f}')
