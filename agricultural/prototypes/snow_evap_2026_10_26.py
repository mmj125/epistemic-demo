"""Soil and residue evaporation on snow days in Cycles (2026-10-26): days with snow_sublimation above 0 against other cold-season days (Dec to Mar), 10 northern fresh94 sites, N=150. Usage: python3 snow_evap_2026_10_26.py"""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
F=json.load(open('sitesets/fresh94.json')); ks=sorted(F,key=lambda k:-F[k][0])[:10]
rows=[]
for site in ks:
    lat,lon=F[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    W=[r for r in csv.DictReader(open(d+"dailyWater.csv")) if r['date'][0]!='#']; shutil.rmtree(d,ignore_errors=True)
    for w in W:
        mo=int(w['date'][5:7])
        if mo in (12,1,2,3): rows.append((float(w['snow_sublimation']),float(w['soil_evaporation']),float(w['residue_evaporation']),float(w['infiltration']),float(w['runoff'])))
A=np.array(rows); sn=A[:,0]>0
print("sites",len(ks),"cold-season days",len(A),"snow-sublimation days",sn.sum())
print("snow days: sublimation %.2f soil evap %.3f residue evap %.3f | other days: soil evap %.3f residue evap %.3f"%(A[sn,0].mean(),A[sn,1].mean(),A[sn,2].mean(),A[~sn,1].mean(),A[~sn,2].mean()))
print("snow days with soil evap above 0.05:",(A[sn,1]>0.05).mean().round(2)," with residue evap above 0.02:",(A[sn,2]>0.02).mean().round(2))
