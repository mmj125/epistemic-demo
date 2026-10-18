"""Engine vs Cycles daily water multiplier by potential transpiration (mm/day), corn, N=150, free engine. Usage: ENGINE_OVR=... python3 corn_water_by_demand_2026_10_18.py"""
import os,sys,json,shutil,csv,datetime,subprocess
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); N=150
    subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; C={}
    for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
        if x['date'][0]=='#' or x['biomass']=='-999': continue
        dt=datetime.date.fromisoformat(x['date']); C[(dt.year,dt.timetuple().tm_yday)]=(1-float(x['water_stress'])/100,float(x['potential_transpiration']),float(x['thermal_time']))
    shutil.rmtree(d,ignore_errors=True)
    E.DIAG_WATER=[]; m.engine(site,wx,soil,cl,N,"leadin"); S=E.DIAG_WATER; E.DIAG_WATER=None
    out=[]
    for y,doy,w,tt,trp,tra,ttd in S:
        if (y,doy) in C and trp>0: out.append((C[(y,doy)][0],C[(y,doy)][1],w,trp,C[(y,doy)][2]))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    A=np.array(R); print("days",len(A))
    print("potential transpiration bin (CYCLES TRp): Cycles W mean / share<0.8   engine W mean / share<0.8   n")
    for lo,hi in ((0,0.5),(0.5,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,8),(8,20)):
        k=(A[:,1]>=lo)&(A[:,1]<hi)
        if k.sum()>200: print(f"  {lo}-{hi}: Cycles {A[k,0].mean():.3f}/{(A[k,0]<.8).mean():.2f}   engine {A[k,2].mean():.3f}/{(A[k,2]<.8).mean():.2f}   n {k.sum()}   mean TRp Cycles {A[k,1].mean():.2f} engine {A[k,3].mean():.2f}")
