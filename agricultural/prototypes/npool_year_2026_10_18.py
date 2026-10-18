"""Year-round nitrate and ammonium pool, engine vs Cycles, by month (2026-10-18). Corn, 24 sites, continuous chain, free run, N=NLEV (default 0). Monthly means of the end-of-day profile pools (kg/ha), site-years 1982 on.
Locates where in the calendar the engine's pool first departs from Cycles' (winter, spring, summer)."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]=os.environ.get("NLEV","0"); sys.path.insert(0,'.')
NLEV=int(os.environ.get("NLEV","0"))
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NLEV}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NLEV}/"
    Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    cy={}
    for r in Nn:
        dt=datetime.date.fromisoformat(r['date']); cy[(dt.year,dt.timetuple().tm_yday)]=(float(r['profile_soil_NO3']),float(r['profile_soil_NH4']),float(r['net_mineralization']),float(r['nitrification']),float(r['NO3_leaching']),float(r['denitrification']),float(r['volatilization']),dt.month)
    E.DIAG_NPOOL=[]; m.engine(site,wx,soil,cl,NLEV,'leadin'); D=E.DIAG_NPOOL; E.DIAG_NPOOL=None
    last={}
    for y,doy,no3,nh4 in D:
        if y is not None: last[(y,doy)]=(no3,nh4)       # last record of the day
    rows=[]
    for k,e in last.items():
        if k in cy and k[0]>=1982: c=cy[k]; rows.append((c[7],c[0],e[0],c[1],e[1],k[1],k[0],hash(site)%100000))
    return np.array(rows)
if __name__=="__main__":
    R=[a for a in Pool(4).map(one,sorted(S)) if len(a)]; A=np.vstack(R); np.save(f'/tmp/w/npool_N{NLEV}.npy',A); print('saved')
    print(f'N={NLEV}: site-days {len(A)}  (days per site-year {len(A)/ (len(R)*36):.0f})')
    print('month | nitrate C / E | ammonium C / E | total mineral C / E')
    for mo in range(1,13):
        s=A[:,0]==mo
        if s.sum()<50: print(f'  {mo:2d}  no engine days'); continue
        f=lambda i:A[s,i].mean(); print(f'  {mo:2d}  | {f(1):5.1f} / {f(2):5.1f} | {f(3):5.2f} / {f(4):5.2f} | {f(1)+f(3):5.1f} / {f(2)+f(4):5.1f}   (n {s.sum()})')
