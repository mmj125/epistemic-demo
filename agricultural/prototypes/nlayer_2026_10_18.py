"""Nitrate by layer, engine vs Cycles (2026-10-18), corn N=0, 24 sites, free run, fallow-season days (Oct to Apr). Cycles layers 1 and 2 from dailySoilLayersCN (mg/kg x thickness x bulk density x 10 = kg/ha), the rest = profile minus layers 1 and 2;
engine layers 1, 2 and the rest from DIAG_NO3 (last record of each day)."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    CN=rd(d+"dailySoilLayersCN.csv"); Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    prof={r['date']:float(r['profile_soil_NO3']) for r in Nn}; cy={}
    for r in CN:
        dt=datetime.date.fromisoformat(r['date']); l1=float(r['NO3.1'])*float(r['thickness.1'])*float(r['bulk_density.1'])*10; l2=(float(r['NO3.2'])*float(r['thickness.2'])*float(r['bulk_density.2'])*10) if 'NO3.2' in r else 0.0
        cy[(dt.year,dt.timetuple().tm_yday)]=(l1,l2,prof[r['date']],dt.month)
    E.DIAG_NO3=[]; m.engine(site,wx,soil,cl,0,'leadin'); D=E.DIAG_NO3; E.DIAG_NO3=None
    last={(y,doy):l for y,doy,l in D if y is not None}; rows=[]
    for k,l in last.items():
        if k in cy and k[0]>=1982 and (cy[k][3]<=4 or cy[k][3]>=10):
            c=cy[k]; rows.append((c[0],c[1],c[2]-c[0]-c[1],l[0],(l[1] if len(l)>1 else 0.0),sum(l[2:]),len(l),sum(l)))
    return np.array(rows)
if __name__=="__main__":
    R=[a for a in Pool(4).map(one,sorted(S)) if len(a)]; A=np.vstack(R); np.save('/tmp/w/nlayer.npy',A)
    f=lambda i:A[:,i].mean()
    print(f'rows {len(A)}  layers in engine {int(A[:,6].mean())}')
    print(f'layer 1  : Cycles {f(0):5.2f}  engine {f(3):5.2f}  (ratio {f(3)/f(0):.2f})')
    print(f'layer 2  : Cycles {f(1):5.2f}  engine {f(4):5.2f}  (ratio {f(4)/f(1):.2f})')
    print(f'deeper   : Cycles {f(2):5.2f}  engine {f(5):5.2f}  (ratio {f(5)/f(2):.2f})')
    print(f'profile  : Cycles {f(0)+f(1)+f(2):5.2f}  engine {f(7):5.2f}')
