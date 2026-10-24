"""Immobilization per unit residue carbon decomposed, Cycles vs engine (2026-10-19): corn N=0, 24 sites, days since harvest. Cycles: dailyN immobilization (sign flipped) and dailyResidue mass loss (aboveground + belowground + root, x 0.42 C).
Engine: DIAG_NFLUX gross immobilized N and residue carbon decomposed. Reports N immobilized per Mg residue C and the C:N equivalent."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); CF=0.42
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    Nn={r['date']:r for r in rd(d+"dailyN.csv")}; H=rd(d+"harvest.csv"); R=rd(d+"dailyResidue.csv"); shutil.rmtree(d,ignore_errors=True)
    mass={r['date']:float(r['aboveground_residue_biomass'])+float(r['belowground_residue_biomass'])+float(r['root_residue_biomass']) for r in R}
    E.DIAG_NFLUX=[]; E.SIXPOOL_DIAG=[]; m.engine(site,wx,soil,cl,0,'leadin'); D=E.DIAG_NFLUX; E.DIAG_NFLUX=None; E.SIXPOOL_DIAG=None
    en={(y,doy):v for y,doy,*v in D if y is not None}; rows=[]
    for h in H:
        hd=datetime.date.fromisoformat(h['date'])
        if hd.year<1982: continue
        for k in range(1,61):
            dd=hd+datetime.timedelta(days=k); dp=dd-datetime.timedelta(days=1); key=(dd.year,dd.timetuple().tm_yday)
            if dd.isoformat() in mass and dp.isoformat() in mass and key in en and dd.isoformat() in Nn:
                loss=mass[dp.isoformat()]-mass[dd.isoformat()]; v=en[key]
                rows.append((k,-float(Nn[dd.isoformat()]['immobilization']),loss*CF,float(Nn[dd.isoformat()]['mineralization']),v[6],v[7],v[4]+v[5]))
    return np.array(rows)
if __name__=="__main__":
    A=np.vstack([a for a in Pool(4).map(one,sorted(S)) if len(a)]); np.save('/tmp/w/nimmob.npy',A)
    print('days since harvest | Cycles: immob N, residue C decomposed (Mg C/ha/d), N per Mg C (C:N) | engine: immob N, residue C, N per Mg C (C:N) | gross mineralization Cycles, engine')
    for lo,hi in ((1,4),(4,8),(8,15),(15,31),(31,61)):
        s=(A[:,0]>=lo)&(A[:,0]<hi); c=A[s].mean(0)
        print(f' {lo:2d}-{hi-1:2d}: {c[1]:.3f}, {c[2]:.4f}, {c[1]/c[2]:6.1f} ({1000/(c[1]/c[2]):.1f}) | {c[4]:.3f}, {c[5]:.4f}, {c[4]/c[5]:6.1f} ({1000/(c[4]/c[5]):.1f}) | {c[3]:.3f}, {c[6]:.3f}')
