"""Growing-season water balance, engine against Cycles, corn N=150, 24 sites, joined by date (2026-10-23): soil evaporation, residue evaporation, transpiration and layer moisture by thermal-time fraction (Cycles' thermal_time / tt_maturity).
Rows exist only from planting to harvest (the engine's history). Usage: python3 water_budget_2026_10_23.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); orig=m.simulate_continuous
m.simulate_continuous=lambda wx,crop,**kw: orig(wx,crop,record_history=True,**kw)
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    C=rd(d+"dailyCornRM.90.csv"); W=rd(d+"dailyWater.csv"); shutil.rmtree(d,ignore_errors=True)
    cyc={}
    for c,w in zip(C,W):
        if c['biomass']=='-999': continue
        dt=datetime.date.fromisoformat(c['date']); cyc[(dt.year,dt.timetuple().tm_yday)]=(float(c['thermal_time'])/1800.0,float(w['soil_evaporation']),float(w['residue_evaporation']),float(w['transpiration']),[float(w.get(f'soil_moisture_content.{i}',0) or 0) for i in (1,2,3,4)],float(w['infiltration']),float(w['runoff']))
    res=m.engine(site,wx,soil,cl,150,'leadin'); rows=[]
    for y,r in res.items():
        if y<1982: continue
        for h in r.get("history") or []:
            k=(y,h["doy"])
            if k in cyc:
                c=cyc[k]; th=h["theta"]+[0]*4
                rows.append([c[0],c[1],h["soil_evap_mm"],c[2],h["res_evap_mm"],c[3],h["transp_mm"]]+c[4]+th[:4])
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); np.save('/tmp/w/water_budget.npy',A); print(len(A),"days")
    print("ttf bin | soil evap mm/d Cycles engine | residue evap Cycles engine | transpiration Cycles engine | theta1..4 engine minus Cycles (m3/m3)")
    for lo in np.arange(0,1.0,0.1):
        k=(A[:,0]>=lo)&(A[:,0]<lo+0.1)
        if k.sum()>200: print(f" {lo:.1f}-{lo+.1:.1f}: {A[k,1].mean():.2f} {A[k,2].mean():.2f} | {A[k,3].mean():.2f} {A[k,4].mean():.2f} | {A[k,5].mean():.2f} {A[k,6].mean():.2f} | "+" ".join(f"{(A[k,11+i]-A[k,7+i]).mean():+.3f}" for i in range(4)))
    print(f"season mean per day: soil evap Cycles {A[:,1].mean():.2f} engine {A[:,2].mean():.2f}; residue evap {A[:,3].mean():.2f} {A[:,4].mean():.2f}; transp {A[:,5].mean():.2f} {A[:,6].mean():.2f}")
