"""Corn harvest index law measured on Cycles v1.5.20 daily output (2026-10-17): per season f_G = (AG biomass at harvest - AG biomass at flowering)/AG biomass at harvest, HI at harvest, 24 sites x N=0,150,400. Fits HI = hx - (hx-ho) exp(-s f_G) and compares with the documented 0.8/0.15/1.3077 and with row 6's 0.760/0.151/1.479; reports mean residual by N and by latitude of documented vs fitted. Usage: python3 corn_hi_law_2026_10_17.py"""
import os,sys,json,csv,datetime,shutil,subprocess,statistics as st
os.environ["N_LEVELS"]="0,150,400"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (0,150,400):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; Y={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999':continue
            dt=datetime.date.fromisoformat(x['date']); Y.setdefault(dt.year,[]).append((float(x['thermal_time']),float(x['aboveground_biomass']),float(x['harvest_index']),float(x['grain_biomass']) if x['grain_biomass']!='-999' else None))
        H={}
        for x in csv.DictReader(open(d+"harvest.csv")):
            if x['date'][0]=='#':continue
            H[int(x['date'][:4])]=(float(x['total_biomass'])-float(x['root_biomass']),float(x['harvest_index']))
        shutil.rmtree(d,ignore_errors=True)
        for y,L in Y.items():
            fl=[r for r in L if r[0]>=1000]
            if y not in H or not fl: continue
            ag_f=fl[0][1]; ag_h,hi=H[y]
            if ag_h>1 and hi>0: out.append((site,lat,N,(ag_h-ag_f)/ag_h,hi))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    import numpy as np
    json.dump(R,open("/tmp/w/hi_law.json","w"))
    fg=np.array([r[3] for r in R]); hi=np.array([r[4] for r in R]); N=np.array([r[2] for r in R]); lat=np.array([r[1] for r in R])
    def law(p,x): return p[0]-(p[0]-p[1])*np.exp(-p[2]*x)
    from scipy.optimize import least_squares
    fit=least_squares(lambda p:law(p,fg)-hi,[0.76,0.15,1.4]).x
    print("seasons",len(R),"fitted hx %.3f ho %.3f s %.3f rms %.4f"%(*fit,np.sqrt(np.mean((law(fit,fg)-hi)**2))))
    doc=np.array([0.8,0.15,1.3077]); print("documented rms %.4f mean residual (law-Cycles) %+.4f"%(np.sqrt(np.mean((law(doc,fg)-hi)**2)),np.mean(law(doc,fg)-hi)))
    for n in (0,150,400):
        k=N==n; print(f" N={n}: f_G mean {fg[k].mean():.3f}  HI Cycles {hi[k].mean():.3f}  documented law {law(doc,fg[k]).mean():.3f}  fitted {law(fit,fg[k]).mean():.3f}")
    for lo,hi_ in ((25,35),(35,40),(40,45),(45,50)):
        k=(lat>=lo)&(lat<hi_)
        if k.sum(): print(f" {lo}-{hi_}N: documented law minus Cycles {np.mean(law(doc,fg[k])-hi[k]):+.4f}  fitted {np.mean(law(fit,fg[k])-hi[k]):+.4f}")
