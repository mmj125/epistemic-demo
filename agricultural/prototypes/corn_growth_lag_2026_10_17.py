"""Timing of the canopy used for daily growth (2026-10-17): in Cycles v1.5.20 corn output, days with no water or N stress and canopy 0.05-0.7 (rising phase). Implied conversion = dTotalBiomass / (canopy_lag x solar) for lag 0 (same-day canopy), 1 (previous day), 2 and the mean of days d and d-1; the right timing minimizes the coefficient of variation. 24 sites, N=150. Usage: python3 corn_growth_lag_2026_10_17.py"""
import os,sys,json,csv,datetime,shutil,subprocess,statistics as st
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); N=150
    subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; rows=[]
    for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
        if x['date'][0]=='#' or x['biomass']=='-999': rows.append(None); continue
        dt=datetime.date.fromisoformat(x['date']); rows.append((dt.year,dt.timetuple().tm_yday,float(x['biomass']),float(x['radiation_interception']),1-float(x['water_stress'])/100,1-float(x['nitrogen_stress'])/100,float(x['temperature_factor'])))
    shutil.rmtree(d,ignore_errors=True); out=[]
    for i in range(3,len(rows)):
        r=rows[i]; p1=rows[i-1]; p2=rows[i-2]; p3=rows[i-3]
        if not (r and p1 and p2 and p3): continue
        y,doy,b,c,w,n,tf=r; dB=(b-p1[2])*100   # g/m2
        if w>=0.999 and n>=0.999 and p1[4]>=0.999 and 0.05<=c<=0.7 and dB>0:
            s=wx[y][doy]['solar']; out.append((dB/s,c,p1[3],p2[3],tf))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    import numpy as np
    A=np.array(R); print("days",len(A))
    for nm,den in (("same-day canopy",A[:,1]),("previous-day canopy",A[:,2]),("two days back",A[:,3]),("mean of d and d-1",(A[:,1]+A[:,2])/2)):
        for tfv in (False,True):
            q=A[:,0]/den/(A[:,4] if tfv else 1.0); print(f"{nm:22s} {'/temperature_factor' if tfv else '':20s}: implied conversion mean {q.mean():.3f} CV {q.std()/q.mean():.3f}")
