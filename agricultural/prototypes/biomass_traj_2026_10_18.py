"""Above-ground biomass trajectory, engine against Cycles by TTf = thermal_time / MATURITY_TT (2026-10-18). Corn CornRM.90, N=150 (set N), 14 sites, every season.
Cycles: dailyCornRM.90 aboveground_biomass and thermal_time. Engine: DIAG_AG and DIAG_WATER (year, doy, water stress, thermal time) appended once per in-season day."""
import os,sys,json,csv,shutil,subprocess,datetime
NL=os.environ.get("NLEV","150"); os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]=NL; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json')); MAT=1800.0
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NL}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NL}/"
    C=rd(d+"daily"+os.environ.get("CFILE","CornRM.90")+".csv"); shutil.rmtree(d,ignore_errors=True)
    cy={}
    for r in C:
        if r['aboveground_biomass']=='-999' or r['thermal_time']=='-999' or r['stage'] not in ('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH','MATURITY'): continue
        cy.setdefault(r['date'][:4],[]).append((float(r['thermal_time'])/MAT,float(r['aboveground_biomass'])))
    E.DIAG_AG=[]; E.DIAG_WATER=[]; res=m.engine(site,wx,soil,cl,int(NL),'leadin'); AG=E.DIAG_AG; W=E.DIAG_WATER; E.DIAG_AG=None; E.DIAG_WATER=None
    # one season at a time: split by year label in DIAG_WATER
    en={}
    for (y,doy,ws,tt_cum,trp,tra,tt),ag in zip(W,AG):
        if y is None: continue
        en.setdefault(str(y),[]).append((tt/MAT,ag))
    out=[]
    for y in set(cy)&set(en):
        c=np.array(cy[y]); e=np.array(en[y])
        for lo in np.arange(0.2,1.0,0.1):
            sc=(c[:,0]>=lo)&(c[:,0]<lo+0.1); se=(e[:,0]>=lo)&(e[:,0]<lo+0.1)
            if sc.sum()>2 and se.sum()>2: out.append((lo,c[sc,1].mean(),e[se,1].mean()))
    return out
if __name__=="__main__":
    ks=sorted(S)[::7][:14]
    with Pool(4) as p: R=p.map(one,ks)
    A=np.array([x for r in R for x in r]); print('N=%s season-bins %d'%(NL,len(A)))
    print(' TTf bin   Cycles ag (Mg/ha)  engine ag   ratio of means')
    for lo in np.arange(0.2,1.0,0.1):
        s=np.isclose(A[:,0],lo)
        if s.sum()>5: print(f"  {lo:.1f}-{lo+0.1:.1f}     {A[s,1].mean():6.2f}            {A[s,2].mean():6.2f}      {A[s,2].mean()/A[s,1].mean():.2f}")
