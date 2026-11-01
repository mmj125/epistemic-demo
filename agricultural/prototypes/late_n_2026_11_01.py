"""Late-season N (2026-11-01): Cycles against the engine by TTf bin for corn or sorghum at a chosen N rate: above-ground N, daily above-ground N uptake, profile mineral N, N factor, above-ground biomass.
Usage: CROPSEL=corn|sorghum NRATE=150 python3 late_n_2026_11_01.py (12 sites of the 24-site set)."""
import sys,os,csv,json,shutil,subprocess,glob,datetime
CS=os.environ.get("CROPSEL","sorghum"); NR=int(os.environ.get("NRATE","150")); os.environ["CROPSEL"]=CS; os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]=str(NR); os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
_orig=m.cev.standard_kwargs; m.cev.standard_kwargs=lambda *a,**k: {**_orig(*a,**k),'record_history':True}
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
SUF,CF,MAT,TTE=(("sor","SorghumMS",2050,65) if CS=="sorghum" else ("","CornRM.90",1800,65))
def job(site):
    N=NR; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); nm=f"{site}{SUF}N{N}"
    subprocess.run(["./Cycles",nm],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}/"
    D=[r for r in csv.DictReader(l for l in open(glob.glob(d+f"daily{CF}.csv")[0]) if not l.startswith('#'))]; DN={r['date']:r for r in csv.DictReader(l for l in open(d+"dailyN.csv") if not l.startswith('#'))}; shutil.rmtree(d,ignore_errors=True)
    res=m.engine(site,wx,soil,cl,N,"leadin"); eng={}
    for y,r in res.items():
        for h in (r.get("history") or []): eng[(y,h["doy"])]=h
    rows=[]; prev={}
    for r in D:
        if r['biomass']=='-999' or r['crop']=='FALLOW': continue
        dt=datetime.date.fromisoformat(r['date']); k=(dt.year,dt.timetuple().tm_yday); x=float(r['thermal_time'])/(MAT-TTE)
        if k not in eng or x>1.0: continue
        h=eng[k]; dn=DN.get(r['date']); cN=float(r['aboveground_nitrogen']); eN=h.get("n_plant") or 0.0
        pc,pe=prev.get(dt.year,(cN,eN)); prev[dt.year]=(cN,eN)
        rows.append([x,float(r['aboveground_biomass']),cN,cN-pc,1-float(r['nitrogen_stress'])/100,(float(dn['profile_soil_NO3'])+float(dn['profile_soil_NH4'])) if dn else np.nan,
                     h.get("ag_mg_ha") or 0.0,eN,eN-pe,h.get("n_stress") or 0.0,(h.get("n_no3") or 0.0)+(h.get("n_nh4") or 0.0)])
    return rows
if __name__=="__main__":
    with Pool(4) as p: R=p.map(job,sorted(S)[:12])
    A=np.array([r for rs in R for r in rs]); print(CS,"N",NR,"days",len(A))
    print("TTf bin | ag biomass C/E | ag N C/E | N uptake kg/ha/day C/E | N factor C/E | profile mineral N C/E")
    for lo,hi in [(0,.2),(.2,.3),(.3,.4),(.4,.5),(.5,.6),(.6,.7),(.7,.8),(.8,.9),(.9,1.01)]:
        k=(A[:,0]>=lo)&(A[:,0]<hi); a=A[k]
        if len(a)<20: continue
        print(f"{lo:.1f}-{hi:.1f} | {a[:,1].mean():5.2f} {a[:,6].mean():5.2f} | {a[:,2].mean():6.1f} {a[:,7].mean():6.1f} | {a[:,3].mean():5.2f} {a[:,8].mean():5.2f} | {a[:,4].mean():.2f} {a[:,9].mean():.2f} | {np.nanmean(a[:,5]):6.1f} {a[:,10].mean():6.1f}")
