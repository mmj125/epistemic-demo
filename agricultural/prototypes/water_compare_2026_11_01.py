"""Water comparison, corn N=150, 24 sites (sitesets/s24.json), current engine against Cycles (2026-11-01).
Growing-season means (Cycles stage VEGETATIVE or REPRODUCTIVE days, engine days with history), reported as engine and Cycles:
water factor (1 - water_stress), potential and actual transpiration, soil evaporation, soil water content by layer, plus the factor Cycles would give from the engine's own supply/demand ratio."""
import os,sys,csv,json,shutil,subprocess,glob,datetime
os.environ["CROPSEL"]="corn"; os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
_o=m.cev.standard_kwargs; m.cev.standard_kwargs=lambda *a,**k: {**_o(*a,**k),'record_history':True}
from multiprocessing import Pool
S=json.load(open('sitesets/s24.json'))
def job(site):
    N=150; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); nm=f"{site}N{N}"
    subprocess.run(["./Cycles",nm],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}/"
    rd=lambda f:[r for r in csv.DictReader(l for l in open(d+f) if not l.startswith('#'))]
    C=rd("dailyCornRM.90.csv"); W=rd("dailyWater.csv"); hdrW=list(W[0].keys()); shutil.rmtree(d,ignore_errors=True)
    Wd={r['date']:r for r in W}
    res=m.engine(site,wx,soil,cl,N,"leadin"); out=[]
    for r in C:
        if r['biomass']=='-999' or r['stage'] not in('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH'): continue
        dt=datetime.date.fromisoformat(r['date']); y=dt.year; doy=dt.timetuple().tm_yday
        if y not in res or not res[y].get('history'): continue
        h={x['doy']:x for x in res[y]['history']}
        if doy not in h: continue
        e=h[doy]; w=Wd.get(r['date'],{})
        out.append((1-float(r['water_stress'])/100,e['water_stress'],float(r['potential_transpiration']),e['trp_mm'],float(w.get('transpiration',np.nan)) if w else np.nan,e['transp_mm'],float(w.get('soil_evaporation',np.nan)) if w else np.nan,e['soil_evap_mm']+e.get('res_evap_mm',0),[float(w.get(c,np.nan)) for c in hdrW if c.startswith('soil_moisture_content')][:6] if w else [], e['theta'][:6],e.get('gr',0.0),dt.month))
    return hdrW,out
if __name__=="__main__":
    with Pool(4) as p: R=p.map(job,sorted(S))
    print("dailyWater columns:",R[0][0])
    A=[x for _,o in R for x in o]; print("growing days",len(A))
    f=lambda i:np.nanmean([a[i] for a in A])
    print(f"water factor      Cycles {f(0):.3f} engine {f(1):.3f}")
    print(f"potential transp  Cycles {f(2):.2f} engine {f(3):.2f} mm/day")
    print(f"actual transp     Cycles {f(4):.2f} engine {f(5):.2f} mm/day")
    print(f"soil evaporation  Cycles {f(6):.2f} engine {f(7):.2f} mm/day")
    wt=np.array([a[10] for a in A]); mo=np.array([a[11] for a in A]); fc=np.array([a[0] for a in A]); fe=np.array([a[1] for a in A])
    print(f"growth-weighted factor Cycles {np.average(fc,weights=wt):.3f} engine {np.average(fe,weights=wt):.3f}")
    for M in (5,6,7,8,9):
        s=mo==M
        if s.sum(): print(f"  month {M}: days {s.sum():6d} factor Cycles {fc[s].mean():.3f} engine {fe[s].mean():.3f}  corr {np.corrcoef(fc[s],fe[s])[0,1]:.2f}  weight share {wt[s].sum()/wt.sum():.2f}")
    th=[(a[8],a[9]) for a in A if len(a[8])>=1]
    if th:
        for L in range(min(4,len(th[0][1]))):
            c=np.nanmean([t[0][L] for t in th if len(t[0])>L]); e=np.nanmean([t[1][L] for t in th])
            print(f"layer {L+1} water content  Cycles {c:.3f} engine {e:.3f}")
