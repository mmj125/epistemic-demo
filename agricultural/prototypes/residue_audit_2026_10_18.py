"""Residue cover audit (2026-10-18). Cycles dailyResidue: radiation_interception (surface residue cover) against aboveground_residue_biomass. (1) fit Cycles' law cover = 1 - exp(-K B) on all days;
(2) compare the amount of residue: engine effective biomass (from its logged cover, B = -ln(1-cover)/0.27) against Cycles' aboveground_residue_biomass by month, in-season days only (corn, N=150, 24 sites)."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
from scipy.optimize import least_squares
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    Re=rd(d+"dailyResidue.csv"); shutil.rmtree(d,ignore_errors=True)
    allp=[(float(r['aboveground_residue_biomass']),float(r['radiation_interception'])) for r in Re if r['aboveground_residue_biomass']!='-999']
    cy={(datetime.date.fromisoformat(r['date']).year,datetime.date.fromisoformat(r['date']).timetuple().tm_yday):(float(r['aboveground_residue_biomass']),float(r['radiation_interception'])) for r in Re}
    E.DIAG_EVAP=[]; m.engine(site,wx,soil,cl,150,'leadin'); EV=E.DIAG_EVAP; E.DIAG_EVAP=None
    cmp=[]
    for (y,doy,se,re_,eto,rc) in EV:
        if y is None or (y,doy) not in cy: continue
        b,c=cy[(y,doy)]; month=(datetime.date(y,1,1)+datetime.timedelta(doy-1)).month
        cmp.append((month,b,c,rc,-np.log(max(1e-9,1-min(rc,0.999)))/E.RESIDUE_COVER_K))
    return allp,cmp
if __name__=="__main__":
    with Pool(4) as p: R=p.map(one,sorted(S))
    P=np.array([x for a,c in R for x in a]); P=P[P[:,0]>=0]
    f=lambda k:(1-np.exp(-k[0]*P[:,0]))-P[:,1]
    r=least_squares(f,[0.27]); print('Cycles residue cover law 1-exp(-K B): K = %.3f, rms %.4f over %d days (engine: K 0.27 on 0.7*Cra/0.4)'%(r.x[0],np.sqrt(np.mean(f(r.x)**2)),len(P)))
    for B in (0.5,1,2,4,6,8):
        s=(P[:,0]>=B*0.8)&(P[:,0]<B*1.25)
        if s.sum()>50: print('  Cycles biomass ~%.1f Mg/ha: median cover %.3f (law %.3f)'%(B,np.median(P[s,1]),1-np.exp(-r.x[0]*B)))
    C=np.array([x for a,c in R for x in c]); print('in-season days',len(C))
    print(' month  Cycles residue biomass  engine effective biomass  ratio | Cycles cover  engine cover')
    for mo in range(4,12):
        s=C[:,0]==mo
        if s.sum()>50: print(f"  {mo:2d}      {C[s,1].mean():6.2f}                 {C[s,4].mean():6.2f}               {C[s,4].mean()/C[s,1].mean():.2f}  |  {C[s,2].mean():.3f}        {C[s,3].mean():.3f}")
