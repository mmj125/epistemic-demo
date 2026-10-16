"""Phenology check (2026-10-15): engine vs Cycles planting date and days from planting to maturity, 28 sites, N=150, continuous chain.
Phenology depends on weather only (no N or water coupling), so errors here are exogenous. Usage: python3 phenology_check.py"""
import sys,os,csv,json,datetime,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
def one(site):
    lat,lon=S.ALL[site];N=150
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    r=m.engine(site,wx,soil,cl,N,'leadin');keys=sorted(r[sorted(r)[0]].keys())
    rows=[]
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')):
        if x['date'][0]=='#':continue
        y=int(x['date'][:4]);hd=datetime.date.fromisoformat(x['date']);pd=datetime.date.fromisoformat(x['planting_date'])
        if y in r:rows.append((y,pd.timetuple().tm_yday,hd.timetuple().tm_yday,r[y].get('plant_doy'),r[y].get('harvest_doy',r[y].get('last_doy')),r[y]['grain']))
    return site,keys,rows
if __name__=="__main__":
    with Pool(4) as p: res=p.map(one,list(S.ALL))
    json.dump(res,open('/tmp/w/phenology.json','w'))
    print('result keys:',res[0][1][:40])
    held=set(m.HELDOUT_SITES);P=[];D=[]
    print('site              plantErr(days eng-Cyc) mean/MAE | season length err (eng-Cyc) mean/MAE')
    for s,k,rows in res:
        a=np.array([[r[1],r[2],r[3] if r[3] is not None else np.nan,r[4] if r[4] is not None else np.nan] for r in rows],float)
        pe=a[:,2]-a[:,0];le=(a[:,3]-a[:,2])-(a[:,1]-a[:,0])
        print('%-16s %6.1f %5.1f | %6.1f %5.1f'%(s,np.nanmean(pe),np.nanmean(abs(pe)),np.nanmean(le),np.nanmean(abs(le))))
