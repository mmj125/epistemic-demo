"""Mineral N pool by month, engine vs Cycles, whole year (2026-10-18): corn N=0, 24 sites, continuous chain, years 1982 on. Engine DIAG_NPOOL (every simulated day), Cycles dailyN. Also Oct-Apr loss/netmin sums from Cycles dailyN."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True); f=lambda r,k:float(r[k]); cy={}
    for r in Nn:
        dt=datetime.date.fromisoformat(r['date']); cy[(dt.year,dt.timetuple().tm_yday)]=(dt.month,f(r,'profile_soil_NO3')+f(r,'profile_soil_NH4'),f(r,'net_mineralization'),f(r,'NO3_leaching')+f(r,'NO3_bypass'),f(r,'volatilization'),f(r,'denitrification'))
    E.DIAG_NPOOL=[]; m.engine(site,wx,soil,cl,0,'leadin'); D=E.DIAG_NPOOL; E.DIAG_NPOOL=None
    last={(y,doy):(a+b) for y,doy,a,b in D if y is not None}; rows=[]
    for k,v in last.items():
        if k in cy and k[0]>=1982: rows.append((*cy[k],v))
    return np.array(rows)
if __name__=="__main__":
    A=np.vstack([a for a in Pool(4).map(one,sorted(S)) if len(a)]); np.save('/tmp/w/nfallow.npy',A)
    print('month: Cycles pool | engine pool | ratio   (n site-days)')
    for mo in range(1,13):
        s=A[:,0]==mo
        if s.sum()>100: print(f'  {mo:2d}: {A[s,1].mean():6.1f} | {A[s,6].mean():6.1f} | {A[s,6].mean()/A[s,1].mean():.2f}  ({s.sum()})')
    w=(A[:,0]<=4)|(A[:,0]>=10)
    print('Cycles Oct-Apr per day: netmin %.3f leach+bypass %.4f volat %.4f denit %.4f'%tuple(A[w,i].mean() for i in (2,3,4,5)))
