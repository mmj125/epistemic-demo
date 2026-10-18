"""In-season daily N flows, engine vs Cycles (2026-10-18): corn N=0, 24 sites, continuous chain, same site-days (engine in-season days, years 1982 on). kg N/ha/day means.
Engine hook DIAG_NSEASON. Cycles dailyN. Closure: pool change + uptake against net mineralization - leaching - volatilization - denitrification."""
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
    Nn=rd(d+"dailyN.csv"); C=rd(d+"dailyCornRM.90.csv"); shutil.rmtree(d,ignore_errors=True)
    f=lambda r,k:float(r[k])
    cy={}; pp=None; pn={}
    for r in C:
        if r['total_nitrogen']!='-999': pn[r['date']]=float(r['total_nitrogen'])
    prevpn=None
    for r in Nn:
        dt=datetime.date.fromisoformat(r['date']); k=(dt.year,dt.timetuple().tm_yday)
        up=(pn[r['date']]-prevpn) if (r['date'] in pn and prevpn is not None) else 0.0
        prevpn=pn.get(r['date'])
        cy[k]=(f(r,'net_mineralization'),f(r,'nitrification'),f(r,'volatilization'),f(r,'denitrification'),f(r,'NO3_leaching')+f(r,'NO3_bypass'),max(up,0.0),f(r,'profile_soil_NO3')+f(r,'profile_soil_NH4'))
    E.DIAG_NSEASON=[]; m.engine(site,wx,soil,cl,NLEV,'leadin'); D=E.DIAG_NSEASON; E.DIAG_NSEASON=None
    last={(y,doy):v for y,doy,*v in D if y is not None}; rows=[]
    for k,v in last.items():
        if k in cy and k[0]>=1982: rows.append((k[1],*cy[k],*v))
    return np.array(rows)
if __name__=="__main__":
    A=np.vstack([a for a in Pool(4).map(one,sorted(S)) if len(a)]); np.save('/tmp/w/nseason.npy',A)
    names=['netmin','nitrif','volat','denit','leach','uptake','pool']
    print(f'N={NLEV} in-season site-days {len(A)}  (Cycles | engine)')
    for i,n in enumerate(names): print(f'  {n:7s} {A[:,1+i].mean():8.4f} | {A[:,8+i].mean():8.4f}')
    for lab,o in (('Cycles',1),('engine',8)):
        loss=A[:,o+2]+A[:,o+3]+A[:,o+4]; src=A[:,o]
        print(f'  {lab}: netmin - losses - uptake per day {np.mean(src-loss-A[:,o+5]):+.4f}  (pool drift is the closure target)')
    print('by month (netmin, uptake, losses=volat+denit+leach, pool)  Cycles | engine')
    for mo,(lo,hi) in {'May':(121,152),'Jun':(152,182),'Jul':(182,213),'Aug':(213,244),'Sep':(244,274)}.items():
        s=(A[:,0]>=lo)&(A[:,0]<hi)
        if s.sum()<200: continue
        c=lambda o:(A[s,o].mean(),A[s,o+5].mean(),(A[s,o+2]+A[s,o+3]+A[s,o+4]).mean(),A[s,o+6].mean())
        print(f'  {mo}: '+' '.join('%.3f'%x for x in c(1))+' | '+' '.join('%.3f'%x for x in c(8)))
