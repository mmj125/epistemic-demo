import sys,os,csv,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
import cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
orig=m.simulate_continuous
def sc(*a,**k):
    k['record_history']=True;return orig(*a,**k)
m.simulate_continuous=sc
import datetime
def one(site):
    lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    r=m.engine(site,wx,soil,cl,0,'leadin')
    Nn={x['date']:float(x['profile_soil_NO3'])+float(x['profile_soil_NH4']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N0/dailyN.csv')) if x['date'][0]!='#'}
    e=[];c=[];eh=[];ch=[]
    for y in sorted(r):
        fs=r[y].get('final_n_state')
        if not fs or f'{y}-12-31' not in Nn: continue
        pool=fs.get('n_nh4',0)+sum(fs['no3_layers']) if fs.get('no3_layers') else fs.get('n_nh4',0)+fs.get('n_no3',0)
        e.append(pool);c.append(Nn[f'{y}-12-31'])
        h=r[y].get('history')
        if h:
            d=(datetime.date(y,1,1)+datetime.timedelta(h[-1]['doy']-1)).isoformat()
            if d in Nn: eh.append(h[-1]['n_pool']);ch.append(Nn[d])
    return site,float(np.mean(eh)),float(np.mean(ch)),float(np.mean(e)),float(np.mean(c))
if __name__=="__main__":
    with Pool(8) as p: res=p.map(one,list(ALL))
    print('N=0 mineral N: harvest day engine/Cycles | Dec 31 engine/Cycles')
    for s,eh,ch,e,c in sorted(res,key=lambda r:r[1]/r[2]): print('  %-13s %6.1f %6.1f r%.2f | %6.1f %6.1f r%.2f'%(s,eh,ch,eh/ch,e,c,e/c))
