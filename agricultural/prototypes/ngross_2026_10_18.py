"""Gross mineralization and immobilization, engine vs Cycles (2026-10-18), corn N=0, 24 sites, fallow-window days, free run, 1982 on (kg N/ha/day).
Cycles: dailyN mineralization and immobilization. Engine: released from soil organic matter and microbes, released from residue, immobilized (reconstructed from the per-layer six-pool diagnostic with the pools' C:N constants)."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    cy={}
    for r in Nn:
        dt=datetime.date.fromisoformat(r['date']); cy[(dt.year,dt.timetuple().tm_yday)]=(float(r['mineralization']),float(r['immobilization']),float(r['net_mineralization']),dt.month)
    E.DIAG_NFLUX=[]; E.SIXPOOL_DIAG=[]; m.engine(site,wx,soil,cl,0,'leadin'); D=E.DIAG_NFLUX; E.DIAG_NFLUX=None; E.SIXPOOL_DIAG=None
    last={(y,doy):v for y,doy,*v in D if y is not None}; rows=[]
    for k,v in last.items():
        if k in cy and k[0]>=1982: c=cy[k]; rows.append((c[3],c[0],c[1],c[2],v[0],v[4],v[5],v[6]))
    return np.array(rows)
if __name__=="__main__":
    A=np.vstack([a for a in Pool(4).map(one,sorted(S)) if len(a)]); np.save('/tmp/w/ngross.npy',A)
    print('month | Cycles: gross min, immob, net | engine: net, rel(SOM+microbes), rel(residue), immob, gross min (sum), net check')
    for mo in list(range(1,5))+list(range(8,13)):
        s=A[:,0]==mo
        if s.sum()<200: continue
        f=lambda i:A[s,i].mean(); print(f'  {mo:2d} | {f(1):6.3f} {f(2):6.3f} {f(3):6.3f} | {f(4):6.3f}  {f(5):6.3f} {f(6):6.3f} {f(7):6.3f}  gross {f(5)+f(6):6.3f}  chk {f(5)+f(6)-f(7):6.3f}  (n {s.sum()})')
    w=(A[:,0]<=4)|(A[:,0]>=10); g=lambda i:A[w,i].mean()
    print('Oct-Apr mean/day: Cycles gross min %.3f immob %.3f net %.3f | engine net %.3f, rel SOM %.3f, rel residue %.3f, immob %.3f, gross %.3f'%(g(1),g(2),g(3),g(4),g(5),g(6),g(7),g(5)+g(6)))
