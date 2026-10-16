"""Module-swap diagnostic: replace one block of the engine with Cycles' own daily values and measure the yield error that
remains. A canopy interception, B water-stress multiplier, C N-stress multiplier, D = A+B+C. Usage: python3 swap_test.py"""
import sys,os,csv,json,datetime,statistics,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
import cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
OVR={'H law clock forced stress':dict(CANOPY_N_POW=3.85,CANOPY_WATER_POW=1.35),'I H + minn start':dict(CANOPY_N_POW=3.85,CANOPY_WATER_POW=1.35),'G supply+canopylaw':dict(CANOPY_N_POW=3.85,CANOPY_WATER_POW=1.35)}
COND={'base':(),'H law clock forced stress':('wclock',),'I H + minn start':('wclock','minn')}
def force(site,N,keys):
    F={}
    NM={r['date']:float(r['net_mineralization']) for r in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyN.csv')) if r['date'][0]!='#'}
    NN={r['date']:(float(r['profile_soil_NO3']),float(r['profile_soil_NH4'])) for r in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyN.csv')) if r['date'][0]!='#'}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        d=datetime.date.fromisoformat(x['date']);y=d.year;doy=d.timetuple().tm_yday
        f=F.setdefault(y,{'canopy':{},'water':{},'nstress':{},'minn':{},'netmin':{},'wclock':{},'nclock':{}})
        if 'minn' in keys and x['date'] in NN: f['minn'][doy]=NN[x['date']]
        if 'wclock' in keys:
            f['wclock'][doy]=1-float(x['water_stress'])/100;f['nclock'][doy]=1-float(x['nitrogen_stress'])/100
        if 'netmin' in keys and x['date'] in NM: f['netmin'][doy]=NM[x['date']]
        if 'canopy' in keys: f['canopy'][doy]=float(x['radiation_interception'])
        if 'water' in keys: f['water'][doy]=1-float(x['water_stress'])/100
        if 'nstress' in keys: f['nstress'][doy]=1-float(x['nitrogen_stress'])/100
    return F
def one(args):
    site,N,name=args;keys=COND[name]
    lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=force(site,N,keys) if keys else None
    for k,v in OVR.get(name,{}).items(): setattr(E,k,v)
    r=m.engine(site,wx,soil,cl,N,'leadin')
    for k in OVR.get(name,{}): setattr(E,k,None if k=='CANOPY_N_POW' else 1.0)
    H={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')):
        if x['date'][0]!='#':H[int(x['date'][:4])]=float(x['grain_yield'])
    ys=[y for y in r if y in H]
    a=np.array([H[y] for y in ys]);b=np.array([r[y]['grain'] for y in ys])
    c=np.corrcoef(a,b)[0,1] if a.std()>1e-9 and b.std()>1e-9 else float('nan')
    return (site,N,name,float(np.abs(a-b).mean()),float((b-a).mean()),float(c),float(a.mean()))
if __name__=="__main__":
    jobs=[(s,N,n) for n in COND for N in (0,150) for s in ALL]
    with Pool(8) as p: res=p.map(one,jobs)
    json.dump(res,open('/tmp/w/swap.json','w'))
    held=set(m.HELDOUT_SITES)
    print('condition      N | MAE tun  held | bias tun  held | corr tun  held')
    for n in COND:
        for N in (0,150):
            rr=[r for r in res if r[1]==N and r[2]==n]
            g=lambda sel,i:np.nanmean([r[i] for r in rr if sel(r[0])])
            T=lambda s:s not in held;Hh=lambda s:s in held
            print('%-12s %3d | %6.3f %6.3f | %+6.3f %+6.3f | %5.3f %5.3f'%(n,N,g(T,3),g(Hh,3),g(T,4),g(Hh,4),g(T,5),g(Hh,5)))
