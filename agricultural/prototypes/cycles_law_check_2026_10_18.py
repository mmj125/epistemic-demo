"""Does Cycles obey the paper's growth law at every stage? (2026-10-18) From Cycles' own daily output only: GR = RUE*CO2scale*canopy*solar, GT = TUE*CO2scale/sqrt(VPD)*T (T = Cycles' actual transpiration, mm),
GB = min(GR,GT); compare with Cycles' daily change in total biomass by thermal-time fraction and by which term binds. Corn, N=NLEV, continuous chain, canopy of the same day and of the previous day tried.
Usage: python3 cycles_law_check_2026_10_18.py N_SITES N"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
NS=int(sys.argv[1]); NLEV=int(sys.argv[2]); os.environ["N_LEVELS"]=str(NLEV)
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NLEV}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NLEV}/"
    C=rd(d+"dailyCornRM.90.csv"); En={r['date']:r for r in rd(d+"dailyEnviron.csv")}; Wt={r['date']:r for r in rd(d+"dailyWater.csv")}; shutil.rmtree(d,ignore_errors=True)
    prev=None; rows=[]
    for r in C:
        if r['biomass']=='-999': prev=None; continue
        dt=datetime.date.fromisoformat(r['date']); y=dt.year; doy=dt.timetuple().tm_yday
        cur=dict(ag=float(r['aboveground_biomass']),rt=float(r['root_biomass']),b=float(r['biomass']),can=float(r['radiation_interception']),tt=float(r['thermal_time']),ns=1-float(r['nitrogen_stress'])/100,tf=float(r['temperature_factor']))
        if prev is not None and doy in wx[y]:
            co2=(E.CO2_PPM_BY_YEAR.get(y,E.CO2_REF_PPM)/E.CO2_REF_PPM)
            rows.append((cur['b']-prev['b'],cur['can'],prev['can'],cur['tt']/rv.CORN['tt_maturity'],wx[y][doy]['solar'],float(En[r['date']]['vapor_pressure_deficit']),float(Wt[r['date']]['transpiration']),cur['ns'],cur['tf'],co2**E.WUE_CO2_EXP,(wx[y][doy]['tx']+wx[y][doy]['tn'])/2,prev['ns'],cur['ag']-prev['ag'],cur['rt']-prev['rt']))
        prev=cur
    return site,np.array(rows)
if __name__=="__main__":
    ks=sorted(S)[:NS]
    with Pool(4) as p: R=p.map(one,ks)
    A=np.vstack([a for s,a in R if len(a)]); np.save(f'/tmp/w/lawcheck2_N{NLEV}.npy',A); print('days',len(A))
