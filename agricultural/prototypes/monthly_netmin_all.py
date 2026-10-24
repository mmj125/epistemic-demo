"""Monthly net N mineralization, engine vs Cycles, mean over all 28 sites (N=0), kg N/ha per month (2026-10-14). Usage: python3 monthly_netmin_all.py [N]"""
import sys,os,csv,datetime,json,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
import rhizo_engine as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
N=int(sys.argv[1]) if len(sys.argv)>1 else 0
for _a in os.environ.get('OVR','').split(';'):
    if _a:setattr(E,_a.split('=')[0],eval(_a.split('=',1)[1]))
def one(site):
    lat,lon=ALL[site];wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    rec=[];o=E.sixpool_ml_step
    def w(*a,**k):
        r=o(*a,**k);f=sys._getframe(1);doy=None
        while f is not None and doy is None:
            ww=f.f_locals.get('w')
            if isinstance(ww,dict) and 'doy' in ww:doy=ww['doy']
            f=f.f_back
        rec.append((doy,r));return r
    E.sixpool_ml_step=w
    try:m.engine(site,wx,soil,cl,N,'leadin')
    finally:E.sixpool_ml_step=o
    yrs=len(wx);cum=np.cumsum([0,31,28,31,30,31,30,31,31,30,31,30,31])
    mon=lambda d:0 if d<=1 else int(np.searchsorted(cum,min(d,365),side='left'))-1
    eng=np.zeros(12)
    for d,r in rec:
        if d is not None:eng[mon(d)]+=r
    cy=np.zeros(12)
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyN.csv')):
        if x['date'][0]!='#':cy[datetime.date.fromisoformat(x['date']).month-1]+=float(x['net_mineralization'])
    return site,eng/yrs,cy/yrs
if __name__=="__main__":
    with Pool(4) as p:res=p.map(one,list(ALL))
    json.dump([(s,e.tolist(),c.tolist()) for s,e,c in res],open(f'/tmp/w/monthly_netmin_all_N{N}.json','w'))
    E_=np.array([r[1] for r in res]);C_=np.array([r[2] for r in res])
    print('month  engine  Cycles  (mean over 28 sites, kg N/ha/month)   | ratio of site-totals engine/Cycles by month, median')
    for i in range(12):print(' %2d   %6.2f  %6.2f                                      | %.2f'%(i+1,E_[:,i].mean(),C_[:,i].mean(),np.median(E_[:,i]/np.where(np.abs(C_[:,i])<0.05,np.nan,C_[:,i]))))
    print('annual  %6.1f  %6.1f'%(E_.sum(1).mean(),C_.sum(1).mean()))
