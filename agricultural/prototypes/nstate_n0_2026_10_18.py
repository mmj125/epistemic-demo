"""N=0 state comparison, free run, current engine (2026-10-18): by month May to Sept, Cycles vs engine, corn, 24 sites, continuous chain, 37 years.
Canopy, N factor, plant N (kg/ha), daily plant N uptake (kg/ha/day), N concentration of total biomass (%), nitrate pool (kg/ha, Cycles profile_soil_NO3 vs engine layer sum)."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]=os.environ.get("NLEV","0"); sys.path.insert(0,'.')
NLEV=int(os.environ.get("NLEV","0"))
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NLEV}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NLEV}/"
    C=rd(d+"dailyCornRM.90.csv"); Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    no3={r['date']:(float(r['profile_soil_NO3']),float(r['profile_soil_NH4'])) for r in Nn}
    cy={}
    for r in C:
        if r['biomass']=='-999': continue
        dt=datetime.date.fromisoformat(r['date']); cy[(dt.year,dt.timetuple().tm_yday)]=(float(r['radiation_interception']),1-float(r['nitrogen_stress'])/100,float(r['total_nitrogen']),float(r['biomass']),no3[r['date']][0],dt.month)
    E.DIAG_STATE=[]; E.DIAG_BIO=[]; E.DIAG_NO3=[]
    m.engine(site,wx,soil,cl,NLEV,'leadin'); D=E.DIAG_STATE; Bm=E.DIAG_BIO; Nl={(y,doy):sum(l) for y,doy,l in E.DIAG_NO3}
    E.DIAG_STATE=None; E.DIAG_BIO=None; E.DIAG_NO3=None
    en={}
    for (y,doy,can,ns,pn),b in zip(D,Bm):
        if y is not None: en[(y,doy)]=(can,ns,pn,b,Nl.get((y,doy),np.nan))
    rows=[]
    for k in sorted(set(cy)&set(en)):
        km=(k[0],k[1]-1)
        if km in cy and km in en and k[0]>=1982:
            c,e=cy[k],en[k]; rows.append((c[5],c[0],e[0],c[1],e[1],c[2],e[2],c[2]-cy[km][2],e[2]-en[km][2],100*c[2]/(c[3]*1000) if c[3]>0.05 else np.nan,100*e[2]/(e[3]*1000) if e[3]>0.05 else np.nan,c[4],e[4]))
    return np.array(rows)
if __name__=="__main__":
    R=[a for a in Pool(4).map(one,sorted(S)) if len(a)]; A=np.vstack(R)
    print(f'N={NLEV}: days {len(A)}')
    print('month | canopy C/E | N factor C/E | plant N kg/ha C/E | uptake kg/ha/d C/E | N conc % C/E | nitrate pool kg/ha C/E')
    for mo in range(5,10):
        s=(A[:,0]==mo)&(A[:,1]>0.02)
        if s.sum()<100: continue
        f=lambda i:np.nanmean(A[s,i])
        print(f'  {mo}   | {f(1):.2f}/{f(2):.2f} | {f(3):.3f}/{f(4):.3f} | {f(5):6.1f}/{f(6):6.1f} | {f(7):5.2f}/{f(8):5.2f} | {f(9):.2f}/{f(10):.2f} | {f(11):5.1f}/{f(12):5.1f}')
