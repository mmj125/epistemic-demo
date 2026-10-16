import sys,os,csv,datetime,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
import cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
orig=m.simulate_continuous
def sc(*a,**k):
    k['record_history']=True;return orig(*a,**k)
m.simulate_continuous=sc
def one(args):
    site,N=args;lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    r=m.engine(site,wx,soil,cl,N,'leadin')
    Nn={x['date']:float(x['profile_soil_NO3'])+float(x['profile_soil_NH4']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyN.csv')) if x['date'][0]!='#'}
    out=[]
    for y in sorted(r):
        h=r[y].get('history')
        if not h: continue
        d=(datetime.date(y,1,1)+datetime.timedelta(h[0]['doy']-1)).isoformat()
        dec=f'{y-1}-12-31'
        out.append((y,h[0]['n_pool'],Nn.get(d),Nn.get(dec)))
    return site,N,out
if __name__=="__main__":
    with Pool(8) as p: res=p.map(one,[(s,N) for s in ALL for N in (0,150)])
    import json;json.dump(res,open('/tmp/w/plantpool.json','w'))
    for N in (0,150):
        print('N=%d  site        engine@plant  Cycles@plant  ratio | Cycles Dec31 prev'%N)
        rows=[]
        for s,n,o in res:
            if n!=N: continue
            o=[x for x in o if x[2] is not None and x[1] is not None and x[3] is not None]
            if o: rows.append((s,np.mean([x[1] for x in o]),np.mean([x[2] for x in o]),np.mean([x[3] for x in o])))
        for r in sorted(rows,key=lambda r:r[1]/r[2]): print('   %-13s %6.1f %6.1f %5.2f | %6.1f'%(r[0],r[1],r[2],r[1]/r[2],r[3]))
        print('   median ratio %.2f  mean engine %.1f mean Cycles %.1f'%(np.median([r[1]/r[2] for r in rows]),np.mean([r[1] for r in rows]),np.mean([r[2] for r in rows])))
