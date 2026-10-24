"""N module with Cycles' canopy and water stress forced (and, with POOL=1, the daily mineral N pools too) (2026-10-19): engine plant N and N factor against Cycles' by thermal-time fraction, corn, 24 sites, N=0/150/400. Isolates the N side from the water and canopy errors."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150,400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    C={}; F={}; P={}
    if os.environ.get('POOL')=='1':
        for r in rd(d+'dailyN.csv'):
            dd=datetime.date.fromisoformat(r['date']); P.setdefault(dd.year,{})[dd.timetuple().tm_yday]=(float(r['profile_soil_NO3']),float(r['profile_soil_NH4']))
    for x in rd(d+"dailyCornRM.90.csv"):
        if x['biomass']=='-999': continue
        dt=datetime.date.fromisoformat(x['date']); y=dt.year; doy=dt.timetuple().tm_yday
        f=F.setdefault(y,{'canopy':{},'water':{}}); f['canopy'][doy]=float(x['radiation_interception']); f['water'][doy]=1-float(x['water_stress'])/100
        C[x['date']]=(float(x['total_nitrogen']),1-float(x['nitrogen_stress'])/100,float(x['thermal_time'])/1800.0,float(x['biomass']))
    shutil.rmtree(d,ignore_errors=True)
    E.FORCE_SERIES=None if os.environ.get('FREE')=='1' else F; E.NPOOL_FORCE=P if os.environ.get('POOL')=='1' else None; E.DIAG_STATE=[]; E.DIAG_BIO=[]; m.engine(site,wx,soil,cl,N,'leadin'); D=E.DIAG_STATE; BIO=E.DIAG_BIO; E.DIAG_BIO=None; E.DIAG_STATE=None; E.FORCE_SERIES=None; E.NPOOL_FORCE=None; rows=[]
    for (y,doy,eie,ns,pn),bio in zip(D,BIO):
        if y is None or y<1982: continue
        dt=(datetime.date(y,1,1)+datetime.timedelta(days=doy-1)).isoformat()
        if dt in C: rows.append((N,C[dt][2],C[dt][0],pn,C[dt][1],ns,C[dt][3],bio))
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150,400)]),[])); np.save('/tmp/w/nmod_cw'+os.environ.get('POOL','0')+os.environ.get('FREE','0')+'.npy',A)
    for N in (0,150,400):
        s=A[:,0]==N; print(f'N={N}: ttf bin | plant N Cycles | engine | ratio || N factor Cycles | engine')
        for lo in np.arange(0.1,1.0,0.15):
            k=s&(A[:,1]>=lo)&(A[:,1]<lo+0.15)&(A[:,2]>1)
            if k.sum()>200: print(f'  {lo:.2f}-{lo+.15:.2f}: {A[k,2].mean():6.1f} | {A[k,3].mean():6.1f} | {A[k,3].mean()/A[k,2].mean():.2f} || {A[k,4].mean():.3f} | {A[k,5].mean():.3f} || biomass Cycles {A[k,6].mean():.2f} engine {A[k,7].mean():.2f}')
