"""Harvest index law audit (2026-10-18): SI.9 HI = HIx - (HIx - HIo) exp(-kHI * fpf), crop file CornRM.90: HIx 0.8, HIo 0.15, kHI 1.0. Does Cycles' own daily output reproduce
its harvest index with kHI = 1 and fpf = share of growth after flowering (aboveground or total biomass)? Corn, N=150, 14 sites, every season."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json'))
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    D=[r for r in csv.DictReader(open(d+"dailyCornRM.90.csv")) if r['date'][0]!='#']
    HC=list(csv.reader(open(d+"harvest.csv"))); hh=HC[0]; HI={}
    for r in HC[2:]:
        if r and r[0][0]!='#' and len(r)>hh.index('harvest_index'): HI[r[0][:4]]=float(r[hh.index('harvest_index')])
    shutil.rmtree(d,ignore_errors=True)
    byyear={}
    for r in D:
        if r['crop']!='FALLOW' and r['stage'] in ('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH','MATURITY') and r['biomass']!='-999': byyear.setdefault(r['date'][:4],[]).append(r)
    res=[]
    for y,s_ in byyear.items():
        st=[r['stage'] for r in s_]
        if 'REPRODUCTIVE_GROWTH' not in st or y not in HI or HI[y]<=0: continue
        i0=st.index('REPRODUCTIVE_GROWTH'); i1=len(s_)-1
        b=np.array([float(r['biomass']) for r in s_]); a=np.array([float(r['aboveground_biomass']) for r in s_])
        res.append((HI[y],(b[i1]-b[i0])/b[i1],(a[i1]-a[i0])/a[i1],['ok']))
    return res
if __name__=="__main__":
    ks=sorted(S)[::7][:14]
    with Pool(4) as p: R=p.map(one,ks)
    A=[x for r in R for x in r]; print('seasons',len(A),'stage labels seen',A[0][3])
    hi=np.array([x[0] for x in A]); ft=np.array([x[1] for x in A]); fa=np.array([x[2] for x in A])
    for lab,f in (('fpf from total biomass',ft),('fpf from aboveground biomass',fa)):
        for k in (1.0,1.3077):
            pred=0.8-(0.8-0.15)*np.exp(-k*f); print(f"{lab:30s} kHI {k:6.4f}: rms {np.sqrt(np.mean((pred-hi)**2)):.4f} bias {np.mean(pred-hi):+.4f}")
    print('Cycles harvest index mean %.3f sd %.3f; mean fpf total %.3f aboveground %.3f'%(hi.mean(),hi.std(),ft.mean(),fa.mean()))
