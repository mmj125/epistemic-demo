"""Engine plant N uptake vs Cycles total_nitrogen at harvest, unforced, 28 sites (2026-10-15). Usage: python3 uptake_compare.py"""
import sys,os,csv,json,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
def one(a):
    site,N=a;lat,lon=S.ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=None;r=m.engine(site,wx,soil,cl,N,'leadin')
    H={int(x['date'][:4]):(float(x['total_nitrogen']),float(x['grain_yield'])) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')) if x['date'][0]!='#'}
    ys=[y for y in r if y in H]
    return site,N,[(H[y][0],r[y]['n_uptake_kg_ha'],H[y][1],r[y]['grain']) for y in ys]
if __name__=="__main__":
    with Pool(4) as p: res=p.map(one,[(s,N) for N in (0,150) for s in S.ALL])
    held=set(m.HELDOUT_SITES)
    for N in (0,150):
        R=[(s,np.array(o)) for s,n,o in res if n==N]
        c=np.concatenate([a for s,a in R]);print(f'N={N}: Cycles plant N {c[:,0].mean():.0f} engine {c[:,1].mean():.0f} kg/ha; per-year corr {np.corrcoef(c[:,0],c[:,1])[0,1]:.2f}; MAE {np.abs(c[:,0]-c[:,1]).mean():.0f}')
        if N==0:
            for s,a in R:print('   %-14s Cycles %5.0f engine %5.0f | grain Cycles %.1f engine %.1f'%(s,a[:,0].mean(),a[:,1].mean(),a[:,2].mean(),a[:,3].mean()))
