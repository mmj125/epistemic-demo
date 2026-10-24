"""Net mineralization by days since harvest, engine vs Cycles (2026-10-18): corn N=0, 24 sites, continuous chain, years 1982 on. Also Cycles' residue mass, N and C:N (C = 0.4 x mass) at harvest."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    Nn=rd(d+"dailyN.csv"); H=rd(d+"harvest.csv"); R={r['date']:r for r in rd(d+"dailyResidue.csv")}; shutil.rmtree(d,ignore_errors=True)
    cy={}
    for r in Nn:
        dt=datetime.date.fromisoformat(r['date']); cy[(dt.year,dt.timetuple().tm_yday)]=float(r['net_mineralization'])
    E.DIAG_NFLUX=[]; m.engine(site,wx,soil,cl,0,'leadin'); D=E.DIAG_NFLUX; E.DIAG_NFLUX=None
    en={(y,doy):v[0] for y,doy,*v in D if y is not None}; rows=[]; info=[]
    for h in H:
        hd=datetime.date.fromisoformat(h['date']); y0=hd.year
        if y0<1982: continue
        r=R.get(h['date']); 
        if r: 
            ab=float(r['aboveground_residue_biomass']); an=float(r['aboveground_residue_nitrogen']); info.append((ab,an,0.4*ab*1000/max(an,1e-6),float(h['aboveground_residue']),float(h['nitrogen_in_residue'])))
        for k in range(1,241):
            dd=hd+datetime.timedelta(days=k); key=(dd.year,dd.timetuple().tm_yday)
            if key in cy and key in en: rows.append((k,cy[key],en[key]))
    return np.array(rows),np.array(info)
if __name__=="__main__":
    out=Pool(4).map(one,sorted(S)); A=np.vstack([a for a,_ in out if len(a)]); I=np.vstack([i for _,i in out if len(i)])
    print('Cycles residue at harvest: mass %.2f Mg/ha, N %.1f kg/ha, C:N %.1f (harvest.csv residue %.2f, N %.1f)'%tuple(I.mean(0)))
    print('days since harvest: netmin Cycles | engine (kg/ha/day), cumulative difference engine-Cycles (kg/ha)')
    cum=0.0
    for lo,hi in ((1,8),(8,15),(15,31),(31,61),(61,101),(101,161),(161,241)):
        s=(A[:,0]>=lo)&(A[:,0]<hi); c,e=A[s,1].mean(),A[s,2].mean(); cum+=(e-c)*(hi-lo)
        print(f'  {lo:3d}-{hi-1:3d}: {c:7.3f} | {e:7.3f}   cum diff {cum:5.2f}   (n {s.sum()})')
