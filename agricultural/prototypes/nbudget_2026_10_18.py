"""Season N budget at N=0, engine vs Cycles (2026-10-18): corn, 24 sites, continuous chain, years 1982 on. Engine: n_uptake_kg_ha, n_leached, n_denitrified, n_volatilized_pool, n2o, nitrate and ammonium left at harvest, plus fallow-window losses.
Cycles: total_nitrogen at harvest (harvest.csv), annual loss fluxes (annualN), mineral pool at harvest date."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]=os.environ.get("NLEV","0"); sys.path.insert(0,'.')
NLEV=int(os.environ.get("NLEV","0"))
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NLEV}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NLEV}/"
    H=rd(d+"harvest.csv"); Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    pool={r['date']:float(r['profile_soil_NO3'])+float(r['profile_soil_NH4']) for r in Nn}
    cy={int(r['date'][:4]):(float(r['total_nitrogen']),pool.get(r['date'],np.nan)) for r in H if r['total_nitrogen'] not in ('-999',)}
    res=m.engine(site,wx,soil,cl,NLEV,'leadin'); rows=[]
    for y,v in res.items():
        if y>=1982 and y in cy and 'n_uptake_kg_ha' in v:
            rows.append((cy[y][0],cy[y][1],v['n_uptake_kg_ha'],v.get('n_remaining_kg_ha',np.nan),v.get('n_leached_kg_ha',0)+v.get('fallow_n_leached',0),v.get('n_denitrified_kg_ha',0),v.get('n_volatilized_pool_kg_ha',0)))
    return np.array(rows)
if __name__=="__main__":
    A=np.vstack([a for a in Pool(4).map(one,sorted(S)) if len(a)]); np.save('/tmp/w/nbudget.npy',A); f=lambda i:np.nanmean(A[:,i])
    print(f'N={NLEV} site-years {len(A)}')
    print(f'plant N at harvest (Cycles total_nitrogen) {f(0):6.1f} kg/ha | engine n_uptake_kg_ha {f(2):6.1f} (ratio {f(2)/f(0):.2f})')
    print(f'mineral pool at harvest: Cycles {f(1):5.1f} | engine remaining {f(3):5.1f}')
    print(f'engine season losses: leached(+fallow) {f(4):.2f} denitrified {f(5):.2f} volatilized(pool) {f(6):.2f}')
    print('uptake percentiles: Cycles p10/p50/p90 %.0f/%.0f/%.0f | engine %.0f/%.0f/%.0f'%(*np.percentile(A[:,0],[10,50,90]),*np.percentile(A[:,2],[10,50,90])))
