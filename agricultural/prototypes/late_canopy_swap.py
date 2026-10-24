"""Payoff of the late-season canopy (2026-10-14): force Cycles' canopy interception only after LATE of thermal time (L), and over the whole
season (F, the upper bound), then read N=0 and N=150 grain error on the 28 sites. Usage: python3 late_canopy_swap.py"""
import sys,os,csv,json,datetime,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S
import rhizo_engine as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
LATE=0.5
def force(site,N,mode):
    F={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        d=datetime.date.fromisoformat(x['date']);doy=d.timetuple().tm_yday
        if mode=='L' and float(x['thermal_time'])/1800.0<LATE:continue
        f=F.setdefault(d.year,{'canopy':{},'water':{},'nstress':{},'minn':{},'netmin':{},'wclock':{},'nclock':{}})
        f['canopy'][doy]=float(x['radiation_interception'])
    return F
COND={'base':'','L late canopy':'L','F full canopy':'F'}
def one(a):
    site,N,name=a;mode=COND[name]
    lat,lon=S.ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=force(site,N,mode) if mode else None
    r=m.engine(site,wx,soil,cl,N,'leadin')
    H={int(x['date'][:4]):float(x['grain_yield']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')) if x['date'][0]!='#'}
    ys=[y for y in r if y in H];a_=np.array([H[y] for y in ys]);b=np.array([r[y]['grain'] for y in ys])
    c=np.corrcoef(a_,b)[0,1] if a_.std()>1e-9 and b.std()>1e-9 else float('nan')
    return (site,N,name,float(np.abs(a_-b).mean()),float((b-a_).mean()),float(c))
if __name__=="__main__":
    with Pool(4) as p: res=p.map(one,[(s,N,n) for n in COND for N in (0,150) for s in S.ALL])
    json.dump(res,open('/tmp/w/late_canopy_swap.json','w'))
    dry={'kansas','colorado'};held=set(m.HELDOUT_SITES)
    groups=(('all 28',lambda s:True),('dry (KS,CO)',lambda s:s in dry),('humid (not KS/CO)',lambda s:s not in dry),('held-out',lambda s:s in held))
    print('condition        N | '+' | '.join('%-22s'%g for g,_ in groups)+'   (MAE / bias / corr)')
    for n in COND:
        for N in (0,150):
            rr=[r for r in res if r[1]==N and r[2]==n];cells=[]
            for g,sel in groups:
                x=[r for r in rr if sel(r[0])];cells.append('%5.2f %+5.2f %4.2f       '%(np.mean([r[3] for r in x]),np.mean([r[4] for r in x]),np.nanmean([r[5] for r in x])))
            print('%-15s %3d | '%(n,N)+' | '.join(cells))
