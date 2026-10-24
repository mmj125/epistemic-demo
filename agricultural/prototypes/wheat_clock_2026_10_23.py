"""Wheat developmental clock (2026-10-23): is Cycles' TTf = thermal time since planting / thermal time at maturity OF THAT SEASON (maturity varies with vernalization and photoperiod), rather than / a fixed 1800?
Cycles winter wheat daily output, 24 sites, N=150 with FALLN=60. For each season x_fixed = thermal_time/1800 and x_season = thermal_time/(thermal_time on the last growing day). Fits (a) the canopy, documented shape (6,-20,-15,16) with free
maximum cover, unstressed days; (b) the realised shoot share of new growth, SI Eq. 8 form with exponent 4, crop-file fsti 0.45 and fstf 0.95, free TTf50. Reports rms for both clocks."""
import os,sys,json,csv,shutil,subprocess
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from scipy.optimize import least_squares
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); CY=m.CY
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
    fs=site+"wheatck"; m.write_inputs(fs,lat,lon,wx,soil,cl); N=150
    open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N)); subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
    CR=rd(d+"dailyWinterWheat.csv"); shutil.rmtree(d,ignore_errors=True)
    seasons=[]; cur=[]
    for x in CR:
        if x['biomass']=='-999':
            if cur: seasons.append(cur); cur=[]
            continue
        cur.append((float(x['thermal_time']),float(x['aboveground_biomass']),float(x['biomass']),float(x['radiation_interception']),float(x['water_stress']),float(x['nitrogen_stress'])))
    if cur: seasons.append(cur)
    rows=[]
    for s in seasons:
        s=np.array(s)
        if len(s)<150: continue
        tm=s[-1,0]
        for i in range(1,len(s)):
            rows.append([s[i,0],tm,s[i,1]-s[i-1,1],s[i,2]-s[i-1,2],s[i,3],s[i,4],s[i,5]])
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); print(len(A),"days; season-end thermal time mean %.0f sd %.0f min %.0f max %.0f"%(A[:,1].mean(),A[:,1].std(),A[:,1].min(),A[:,1].max()))
    f=lambda x,e: e/(1+np.exp(6-20*x)+np.exp(-15+16*x))
    k=(A[:,5]<2)&(A[:,6]<2)&(A[:,0]>0)
    for nm,x in (("fixed 1800",A[:,0]/1800.0),("season maturity",A[:,0]/A[:,1])):
        r=least_squares(lambda p:f(x[k],p[0])-A[k,4],[0.9]); print(f"canopy, documented shape, {nm:16s}: rms {np.sqrt(np.mean(r.fun**2)):.4f} eix {r.x[0]:.3f} ({k.sum()} days)")
    g=(A[:,3]>0.05)&(A[:,2]>0)&(A[:,2]/np.maximum(A[:,3],1e-9)<1.2)
    share=np.clip(A[g,2]/A[g,3],0,1)
    for nm,x in (("fixed 1800",A[g,0]/1800.0),("season maturity",A[g,0]/A[g,1])):
        h=lambda p:0.45+(0.95-0.45)/(1+(p[0]/np.maximum(x,1e-6))**4)-share
        r=least_squares(h,[0.35]); print(f"shoot share, SI Eq. 8, {nm:16s}: rms {np.sqrt(np.mean(r.fun**2)):.4f} TTf50 {r.x[0]:.3f} ({g.sum()} days)")
