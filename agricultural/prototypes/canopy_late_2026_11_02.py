"""Late-season canopy, corn N=150, 24 sites (sitesets/s24.json): engine radiation interception against Cycles' by thermal time bin and by Cycles' stress after flowering (2026-11-02).
Bins use thermal time as a fraction of maturity (1800). Stress classes are terciles of Cycles' mean water stress and of mean N stress over days after flowering (FLOW 1000)."""
import os,sys,csv,json,shutil,subprocess,datetime
os.environ["CROPSEL"]="corn"; os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
_o=m.cev.standard_kwargs; m.cev.standard_kwargs=lambda *a,**k: {**_o(*a,**k),'record_history':True}
from multiprocessing import Pool
S=json.load(open('sitesets/s24.json')); MAT=1800.0; FLOW=1000.0
def job(site):
    N=150; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); nm=f"{site}N{N}"
    subprocess.run(["./Cycles",nm],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}/"
    C=[r for r in csv.DictReader(l for l in open(d+"dailyCornRM.90.csv") if not l.startswith('#'))]; shutil.rmtree(d,ignore_errors=True)
    res=m.engine(site,wx,soil,cl,N,"leadin"); yrs={}
    for r in C:
        if r['biomass']=='-999' or r['stage'] not in('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH'): continue
        dt=datetime.date.fromisoformat(r['date']); y=dt.year
        if y not in res or not res[y].get('history'): continue
        h={x['doy']:x for x in res[y]['history']}; doy=dt.timetuple().tm_yday
        if doy not in h: continue
        yrs.setdefault(y,[]).append((float(r['thermal_time'])/MAT,float(r['radiation_interception']),h[doy]['canopy'],float(r['water_stress']),float(r['nitrogen_stress'])))
    out=[]
    for y,v in yrs.items():
        a=np.array(v); post=a[a[:,0]>=FLOW/MAT]
        if len(post)<5: continue
        out.append((a,post[:,3].mean(),post[:,4].mean()))
    return out
if __name__=="__main__":
    with Pool(4) as p: R=[x for o in p.map(job,sorted(S)) for x in o]
    print("site-years",len(R))
    bins=[0.0,0.3,0.45,0.55,0.65,0.75,0.85,0.95,1.5]
    def tab(sel,label):
        if not sel: print(label,"empty class"); return
        A=np.vstack([r[0] for r in sel]); print(label,"site-years",len(sel))
        for lo,hi in zip(bins[:-1],bins[1:]):
            s=(A[:,0]>=lo)&(A[:,0]<hi)
            if s.sum()>20: print(f"  TTf {lo:.2f}-{hi:.2f}: Cycles {A[s,1].mean():.3f} engine {A[s,2].mean():.3f} diff {A[s,2].mean()-A[s,1].mean():+.3f}")
    tab(R,"all")
    for nm,idx in (("water",1),("N",2)):
        q=np.percentile([r[idx] for r in R],[33.3,66.7])
        for lab,sel in (("low",[r for r in R if r[idx]<q[0]]),("mid",[r for r in R if q[0]<=r[idx]<q[1]]),("high",[r for r in R if r[idx]>=q[1]])):
            tab(sel,f"{nm} stress after flowering {lab} (Cycles mean {np.mean([r[idx] for r in sel]) if sel else float("nan"):.1f} %)")
