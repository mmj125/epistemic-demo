"""Early-season N at N=0 (2026-10-31), corn, 12 sites, continuous chain: Cycles against the engine by TTf bin: above-ground biomass, above-ground N, N concentration, profile mineral N, N factor.
Cycles columns: aboveground_biomass (Mg/ha), aboveground_nitrogen (kg/ha), aboveground_nitrogen_concentration (g/kg), nitrogen_stress (percent), dailyN profile_soil_NO3 + profile_soil_NH4 (kg/ha). Engine: history ag_mg_ha, n_plant, n_stress, n_no3, n_nh4."""
import sys,os,csv,json,shutil,subprocess,datetime
os.environ["CROPSEL"]="corn"; os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
_orig=m.cev.standard_kwargs; m.cev.standard_kwargs=lambda *a,**k: {**_orig(*a,**k),'record_history':True}
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def job(site):
    N=0; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    D=[r for r in csv.DictReader(open(d+"dailyCornRM.90.csv")) if r['date'][0]!='#']; DN={r['date']:r for r in csv.DictReader(open(d+"dailyN.csv")) if r['date'][0]!='#'}; shutil.rmtree(d,ignore_errors=True)
    res=m.engine(site,wx,soil,cl,N,"leadin"); eng={}
    for y,r in res.items():
        for h in (r.get("history") or []): eng[(y,h["doy"])]=h
    rows=[]
    for r in D:
        if r['biomass']=='-999' or r['crop']=='FALLOW': continue
        dt=datetime.date.fromisoformat(r['date']); k=(dt.year,dt.timetuple().tm_yday); x=float(r['thermal_time'])/1735.0
        if k not in eng or x>1.0: continue
        h=eng[k]; dn=DN.get(r['date'])
        rows.append([x,float(r['aboveground_biomass']),float(r['aboveground_nitrogen']),float(r['aboveground_nitrogen_concentration']),1-float(r['nitrogen_stress'])/100,
                     (float(dn['profile_soil_NO3'])+float(dn['profile_soil_NH4'])) if dn else np.nan,
                     h.get("ag_mg_ha") or 0.0,h.get("n_plant") or 0.0,h.get("n_stress") or 0.0,(h.get("n_no3") or 0.0)+(h.get("n_nh4") or 0.0)])
    return rows
if __name__=="__main__":
    with Pool(4) as p: R=p.map(job,sorted(S)[:12])
    A=np.array([r for rs in R for r in rs]); print("days",len(A))
    print("TTf bin | ag biomass Mg/ha C/E | ag N kg/ha C/E | N conc % C/E (engine = N/biomass) | N factor C/E | profile mineral N kg/ha C/E")
    for lo,hi in [(0,.1),(.1,.2),(.2,.3),(.3,.4),(.4,.6),(.6,.8),(.8,1.01)]:
        k=(A[:,0]>=lo)&(A[:,0]<hi); a=A[k]
        ec=np.where(a[:,6]>0.02,a[:,7]/(10*a[:,6]),np.nan)   # engine plant N kg/ha over Mg/ha x 10 = %
        cc=np.where(a[:,1]>0.02,a[:,2]/(10*a[:,1]),np.nan)
        print(f"{lo:.1f}-{hi:.1f} | {a[:,1].mean():6.2f} {a[:,6].mean():6.2f} | {a[:,2].mean():6.1f} {a[:,7].mean():6.1f} | {np.nanmean(cc):5.2f} {np.nanmean(ec):5.2f} | {a[:,4].mean():.2f} {a[:,8].mean():.2f} | {np.nanmean(a[:,5]):6.1f} {a[:,9].mean():6.1f}")
