"""Check the engine's N stress law on Cycles' own columns (2026-10-17): r = (aboveground N / aboveground biomass) / n_critical_pct(W) with W = Cycles' total biomass (the quantity the engine passes), stress = 0.764 x clip((0.641-r)/0.36)^0.9; compare with Cycles' reported nitrogen_stress by thermal-time decile, N=0 and 150, 24 sites. Also W = aboveground biomass and W = total biomass x 0.6-retained version for comparison. Usage: python3 corn_nstress_law_check_2026_10_17.py"""
import os,sys,json,csv,shutil,subprocess
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (0,150):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999': continue
            tot=float(x['biomass']); ag=float(x['aboveground_biomass']); agn=float(x['aboveground_nitrogen']); st=float(x['nitrogen_stress'])/100
            if ag>0.3: out.append((N,float(x['thermal_time'])/1800.0,tot,ag,agn,st))
        shutil.rmtree(d,ignore_errors=True)
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    import numpy as np
    A=np.array(R); crop=rv.CORN
    def law(w,ag,agn):
        pct=agn/(ag*100)*100/1.0  # kg/ha over (Mg/ha*1000) -> %
        pct=agn/(ag*10)  # agn kg/ha, ag Mg/ha => kg/Mg /10 = %
        rr=np.array([pct_i/E.n_critical_pct(w_i,crop) for pct_i,w_i in zip(pct,w)])
        return 0.764*np.clip((0.641-rr)/0.36,0,1)**0.9, rr
    for lab,w in (("W=total biomass",A[:,2]),("W=aboveground",A[:,3])):
        s,rr=law(w,A[:,3],A[:,4]); print(lab)
        for N in (0,150):
            for lo in (0.2,0.4,0.6,0.8):
                k=(A[:,0]==N)&(A[:,1]>=lo)&(A[:,1]<lo+.2)
                if k.sum()>100: print(f"  N={N} ttf {lo:.1f}-{lo+.2:.1f}: Cycles stress {A[k,5].mean():.3f} law {s[k].mean():.3f} (r mean {rr[k].mean():.2f}) rms {np.sqrt(np.mean((s[k]-A[k,5])**2)):.3f}")
