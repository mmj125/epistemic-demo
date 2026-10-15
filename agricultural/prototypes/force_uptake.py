"""Split nitrogen stress into plant N uptake (supply) and the stress function (2026-10-15). U forces plant N content to Cycles' own daily total_nitrogen
(engine biomass and stress function unchanged); N forces the stress multiplier; C forces canopy. Usage: python3 force_uptake.py"""
import sys,os,csv,json,datetime,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
SUBS=['','U','N','C','CU','CN']
def force(site,N,sub):
    F={}
    if 'N' in sub or 'C' in sub:
        F=S.force(site,N,tuple(k for b in sub if b in 'CN' for k in {'C':('canopy',),'N':('nstress',)}[b]))
    if 'U' in sub:
        for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
            if x['date'][0]=='#' or x['biomass']=='-999':continue
            d=datetime.date.fromisoformat(x['date'])
            F.setdefault(d.year,{k:{} for k in ('canopy','water','nstress','minn','netmin','wclock','nclock')}).setdefault('plantn',{})[d.timetuple().tm_yday]=float(x['total_nitrogen'])
    return F or None
def one(a):
    site,N,sub=a;lat,lon=S.ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=force(site,N,sub)
    r=m.engine(site,wx,soil,cl,N,'leadin')
    H={int(x['date'][:4]):float(x['grain_yield']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')) if x['date'][0]!='#'}
    ys=[y for y in r if y in H];a_=np.array([H[y] for y in ys]);b=np.array([r[y]['grain'] for y in ys])
    return site,N,sub,float(np.abs(a_-b).mean()),float((b-a_).mean())
if __name__=="__main__":
    with Pool(4) as p: res=p.map(one,[(s,N,sub) for sub in SUBS for N in (0,150) for s in S.ALL],chunksize=4)
    json.dump(res,open('/tmp/w/force_uptake.json','w'))
    held=set(m.HELDOUT_SITES)
    base={N:np.mean([r[3] for r in res if r[1]==N and r[2]=='' and r[0] in held]) for N in (0,150)}
    print('forced | N=0 all held (gap removed) | N=150 all held (gap removed)')
    for sub in SUBS:
        c=[]
        for N in (0,150):
            a=np.mean([r[3] for r in res if r[1]==N and r[2]==sub]);h=np.mean([r[3] for r in res if r[1]==N and r[2]==sub and r[0] in held])
            c.append('%5.2f %5.2f (%3d%%)'%(a,h,round(100*(base[N]-h)/base[N])))
        print('%-6s | %s | %s'%(sub or 'none',c[0],c[1]))
