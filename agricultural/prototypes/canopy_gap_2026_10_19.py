"""Free-run canopy against Cycles' radiation interception (2026-10-19): corn, 24 sites, N=0/150/400, continuous chain, engine free (nothing forced). Joined by date; binned by Cycles' thermal-time fraction (thermal_time/1800).
Reports mean canopy Cycles | engine, and the share of the season's radiation intercepted (sum of canopy x 1)."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150,400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    C={}
    for r in rd(d+"dailyCornRM.90.csv"):
        if r['biomass']=='-999': continue
        C[r['date']]=(float(r['radiation_interception']),float(r['thermal_time'])/1800.0,float(r['water_stress']),float(r['nitrogen_stress']))
    shutil.rmtree(d,ignore_errors=True)
    E.DIAG_STATE=[]; m.engine(site,wx,soil,cl,N,'leadin'); D=E.DIAG_STATE; E.DIAG_STATE=None; rows=[]
    for y,doy,eie,ns,cn in D:
        if y is None or y<1982: continue
        dt=(datetime.date(y,1,1)+datetime.timedelta(days=doy-1)).isoformat()
        if dt in C: rows.append((N,C[dt][1],C[dt][0],eie,C[dt][2],C[dt][3]))
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150,400)]),[])); np.save('/tmp/w/canopy_gap.npy',A); print(len(A),'days')
    for N in (0,150,400):
        s=A[:,0]==N; print(f'N={N}: ttf bin | Cycles canopy | engine canopy | ratio')
        for lo in np.arange(0,1.05,0.1):
            k=s&(A[:,1]>=lo)&(A[:,1]<lo+0.1)
            if k.sum()>200: print(f'  {lo:.1f}-{lo+.1:.1f}: {A[k,2].mean():.3f} | {A[k,3].mean():.3f} | {A[k,3].mean()/max(A[k,2].mean(),1e-6):.2f}')
        print(f'  season mean canopy Cycles {A[s,2].mean():.3f} engine {A[s,3].mean():.3f}')
