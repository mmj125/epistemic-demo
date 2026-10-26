"""Soil evaporation demand allocation under a canopy (2026-10-26). On wet days (rain that day, or layer-1 water above 0.95 of field capacity) Cycles' soil_evaporation / ETo is compared with the engine's assumption (1 - canopy)(1 - residue cover),
by canopy bin. Cycles output: dailyWater.csv, dailyCornRM.90.csv (radiation_interception), dailyResidue.csv (radiation_interception). ETo and rain from the engine's weather. Usage: python3 evap_demand_2026_10_26.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
S=json.load(open('/tmp/w/s24.json')); rows=[]
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
for site in sorted(S)[:10]:
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    W=rd(d+"dailyWater.csv"); C=rd(d+"dailyCornRM.90.csv"); R=rd(d+"dailyResidue.csv"); shutil.rmtree(d,ignore_errors=True)
    crop={r['date']:r for r in C}; res={r['date']:r for r in R}
    E.DIAG_EVAP=[]; E._DIAG_YEAR=None; m.engine(site,wx,soil,cl,150,'leadin'); DE=E.DIAG_EVAP; E.DIAG_EVAP=None
    eto={(y,doy):e for (y,doy,ev,re,e,rc) in DE if y is not None}
    fc1=0.0
    for w in W:
        dt=datetime.date.fromisoformat(w['date']); cr=crop.get(w['date']); k=(dt.year,dt.timetuple().tm_yday)
        if cr is None or k not in eto: continue
        rows.append((site,w['date'],float(w['soil_evaporation']),float(w['residue_evaporation']),float(w['infiltration']),float(w['soil_moisture_content.1']),fc1,float(cr['radiation_interception']),float(res[w['date']]['radiation_interception']),eto[k]))
json.dump(rows,open('/tmp/w/evap_demand_rows.json','w')); print(len(rows))
