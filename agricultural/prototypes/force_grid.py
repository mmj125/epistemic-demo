"""Forcing grid (2026-10-15): force every subset of four state blocks to Cycles' own daily values and read the grain MAE that remains.
C canopy interception, W water stress (plus the stress clocks), N nitrogen stress, P planting-day mineral N pool. Usage: python3 force_grid.py"""
import sys,os,csv,json,itertools,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
BLK={'C':('canopy',),'W':('water','wclock'),'N':('nstress',),'P':('minn',)}
SUBS=[''.join(c) for r in range(0,5) for c in itertools.combinations('CWNP',r)]
def one(a):
    site,N,sub=a;lat,lon=S.ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    keys=tuple(k for b in sub for k in BLK[b])
    E.FORCE_SERIES=S.force(site,N,keys) if keys else None
    r=m.engine(site,wx,soil,cl,N,'leadin')
    H={int(x['date'][:4]):float(x['grain_yield']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')) if x['date'][0]!='#'}
    ys=[y for y in r if y in H];a_=np.array([H[y] for y in ys]);b=np.array([r[y]['grain'] for y in ys])
    return site,N,sub,float(np.abs(a_-b).mean()),float((b-a_).mean())
if __name__=="__main__":
    with Pool(4) as p: res=p.map(one,[(s,N,sub) for sub in SUBS for N in (0,150) for s in S.ALL],chunksize=4)
    json.dump(res,open('/tmp/w/force_grid.json','w'))
    held=set(m.HELDOUT_SITES)
    print('forced   | N=0: all  held  | N=150: all  held   (grain MAE Mg/ha; % of base gap removed in brackets, held-out)')
    base={N:np.mean([r[3] for r in res if r[1]==N and r[2]=='' and r[0] in held]) for N in (0,150)}
    for sub in SUBS:
        cells=[]
        for N in (0,150):
            a=np.mean([r[3] for r in res if r[1]==N and r[2]==sub]);h=np.mean([r[3] for r in res if r[1]==N and r[2]==sub and r[0] in held])
            cells.append('%5.2f %5.2f (%3d%%)'%(a,h,round(100*(base[N]-h)/base[N])))
        print('%-8s | %s | %s'%(sub or 'none',cells[0],cells[1]))
