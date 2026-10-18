"""Fallow-season N fluxes, engine vs Cycles (2026-10-18): net mineralization, nitrification, volatilization, denitrification (kg N/ha/day, means over Oct to Apr site-days), corn N=0, 24 sites, free run, years 1982 on."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    cy={}
    for r in Nn:
        dt=datetime.date.fromisoformat(r['date']); cy[(dt.year,dt.timetuple().tm_yday)]=(float(r['net_mineralization']),float(r['nitrification']),float(r['volatilization']),float(r['denitrification']),dt.month)
    E.DIAG_NFLUX=[]; m.engine(site,wx,soil,cl,0,'leadin'); D=E.DIAG_NFLUX; E.DIAG_NFLUX=None
    last={(y,doy):v for y,doy,*v in D if y is not None}; rows=[]
    for k,v in last.items():
        if k in cy and k[0]>=1982: c=cy[k]; rows.append((c[4],*c[:4],*v))
    return np.array(rows)
if __name__=="__main__":
    A=np.vstack([a for a in Pool(4).map(one,sorted(S)) if len(a)]); np.save('/tmp/w/nflux.npy',A)
    print('month | net mineralization C / E | nitrification C / E | volatilization C / E | denitrification C / E   (kg N/ha/day)')
    for mo in list(range(1,5))+list(range(8,13)):
        s=A[:,0]==mo
        if s.sum()<200: continue
        f=lambda i:A[s,i].mean(); print(f'  {mo:2d} | {f(1):6.3f} / {f(5):6.3f} | {f(2):6.3f} / {f(6):6.3f} | {f(3):6.4f} / {f(7):6.4f} | {f(4):6.4f} / {f(8):6.4f}   (n {s.sum()})')
    w=(A[:,0]<=4)|(A[:,0]>=10)
    print('Oct-Apr sum per day: net min C %.3f E %.3f | nitrif C %.3f E %.3f | volat C %.4f E %.4f | denit C %.4f E %.4f'%tuple(A[w,i].mean() for i in (1,5,2,6,3,7,4,8)))
