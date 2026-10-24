import sys,os,csv,json,datetime,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, rhizo_engine as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
def force(site,N,keys):
    F=S.force(site,N,[k for k in keys if k!='loss'])
    if 'loss' in keys:
        L={}
        for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyN.csv')):
            if x['date'][0]=='#':continue
            d=datetime.date.fromisoformat(x['date']);L[(d.year,d.timetuple().tm_yday)]=float(x['NO3_leaching'])+float(x['denitrification'])
        for y,f in F.items():
            f['loss']={doy:L[(y,doy)] for doy in list(f['canopy'].keys() or f['nstress'].keys() or f['netmin'].keys() or []) if (y,doy) in L}
            if not f['loss']:
                f['loss']={doy:v for (yy,doy),v in L.items() if yy==y and 100<=doy<=280}
    return F
def one(a):
    site,N,keys=a;lat,lon=S.ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=force(site,N,keys) if keys else None
    r=m.engine(site,wx,soil,cl,N,'leadin')
    H={int(x['date'][:4]):float(x['grain_yield']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')) if x['date'][0]!='#'}
    return site,N,keys,[(r[y]['grain'],H[y],r[y].get('n_uptake_kg_ha',0)) for y in r if y in H]
if __name__=="__main__":
    C=((),('loss',),('loss','netmin'),('nstress',),('loss','nstress'))
    jobs=[(s,150,k) for s in S.ALL for k in C]
    with Pool(4) as p:res=p.map(one,jobs)
    held=set(m.HELDOUT_SITES)
    for k in C:
        for g,sel in (('tuning',lambda s:s not in held),('held',lambda s:s in held)):
            a=np.array([x for s,n,kk,rows in res if kk==k and sel(s) for x in rows])
            print(150,k,g,'MAE %.3f bias %+.3f uptake %.0f'%(np.abs(a[:,0]-a[:,1]).mean(),(a[:,0]-a[:,1]).mean(),a[:,2].mean()),flush=True)
