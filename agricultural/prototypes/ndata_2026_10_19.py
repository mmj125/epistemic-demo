"""Daily N transformation data from Cycles for documented-form tests (2026-10-19): corn N=0/150/400, 24 sites, years 1982 on. Saves /tmp/w/ndata.npz, array A with columns
0 N, 1 nitrification, 2 volatilization, 3 denitrification, 4 N2O nitrif, 5 N2O denit, 6 infiltration, 7 drainage, 8 doy, 9 site index, 10 year, 11 transpiration, 12 SOM resp C, 13 residue resp C,
then per layer 1..4 (10 columns each, from 14): NO3 kg/ha, NH4 kg/ha, NO3 mg/kg, NH4 mg/kg, composite factor, theta, saturation theta, soil T, thickness m, bulk density Mg/m3."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150,400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    Nn={r['date']:r for r in rd(d+"dailyN.csv")}; L={r['date']:r for r in rd(d+"dailySoilLayersCN.csv")}; W={r['date']:r for r in rd(d+"dailyWater.csv")}; Cc={r['date']:r for r in rd(d+"dailySoilC.csv")}; En={r['date']:r for r in rd(d+"dailyEnviron.csv")}; shutil.rmtree(d,ignore_errors=True)
    sat=[m.saxton_rawls(l["sand"],l["clay"],l["soc"]*m.OM_FROM_SOC)["sat"] for l in soil]; rows=[]
    for dt,l in L.items():
        if dt not in Nn or dt not in W or dt not in Cc or dt not in En or int(dt[:4])<1982: continue
        date=datetime.date.fromisoformat(dt)
        row=[N,float(Nn[dt]['nitrification']),float(Nn[dt]['volatilization']),float(Nn[dt]['denitrification']),float(Nn[dt]['N2O_from_nitrification']),float(Nn[dt]['N2O_from_denitrification']),float(W[dt]['infiltration']),float(W[dt]['drainage']),date.timetuple().tm_yday,SITES.index(site),date.year,float(W[dt]['transpiration']),float(Cc[dt]['soil_organic_matter_respired_carbon']),float(Cc[dt]['residue_respired_carbon'])]
        for i in range(1,5):
            if f'NO3.{i}' in l:
                bd=float(l[f'bulk_density.{i}']); thick=float(l[f'thickness.{i}']); f=bd*thick*10.0
                row+=[float(l[f'NO3.{i}'])*f,float(l[f'NH4.{i}'])*f,float(l[f'NO3.{i}']),float(l[f'NH4.{i}']),float(l[f'composite_factor.{i}']),float(W[dt][f'soil_moisture_content.{i}']),sat[i-1],float(En[dt][f'soil_temperature.{i}']),thick,bd]
            else: row+=[0]*10
        rows.append(row)
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,[(s,N) for s in SITES for N in (0,150,400)]),[])); np.savez('/tmp/w/ndata.npz',A=A); print(A.shape)
