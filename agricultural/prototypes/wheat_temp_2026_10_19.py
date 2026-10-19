"""Wheat radiation-limited effective RUE against mean air temperature in Cycles output (2026-10-19): clean days (water stress and N stress under 2 percent, transpiration not binding approximated by water stress), 16 fresh sites, N=150 and 0, FALLN=60.
eff = dTotalBiomass x 100 / (solar x canopy of the previous day) in g/MJ, divided by the crop-file RUE 1.6 x CO2 scale. Compared with the engine's radiation_temp_factor for wheat."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); os.environ["FALLN"]="60"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E, run_validation_rotation2 as r2
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatU"; m.write_inputs(fs,lat,lon,wx,soil,cl); rows=[]
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N)); subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
        prev=None
        for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999': prev=None; continue
            dt=datetime.date.fromisoformat(x['date']); y=dt.year; doy=dt.timetuple().tm_yday
            cur=(float(x['biomass']),float(x['radiation_interception']))
            if prev and doy in wx[y] and y>=1981 and float(x['water_stress'])<2 and float(x['nitrogen_stress'])<2 and prev[1]>0.05:
                w=wx[y][doy]; tm=(w['tx']+w['tn'])/2; co2=E.CO2_PPM_BY_YEAR.get(y,E.CO2_REF_PPM)/E.CO2_REF_PPM
                rows.append((tm,(cur[0]-prev[0])*100/(w['solar']*prev[1])/1.6,float(x['temperature_factor']),doy))
            prev=cur
        shutil.rmtree(d,ignore_errors=True)
    return rows
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:16]
    with Pool(4) as p: R=sum(p.map(one,[(k,S[k]) for k in ks]),[])
    A=np.array(R); np.save('/tmp/w/wheat_temp.npy',A); print(len(A),'clean days')
    w=r2.WHEAT; print('tmean bin: n | Cycles eff RUE / 1.6 (median) | Cycles temperature_factor | engine radiation_temp_factor')
    for lo in range(-5,30,3):
        k=(A[:,0]>=lo)&(A[:,0]<lo+3)
        if k.sum()>100: print(f' {lo:3d}-{lo+3:3d}: {k.sum():5d} | {np.median(A[k,1]):.3f} | {np.median(A[k,2]):.3f} | {E.radiation_temp_factor(lo+1.5,w["tr_min_t"],w["rad_temp_floor"],w["rad_temp_plateau_t"]):.3f}')
