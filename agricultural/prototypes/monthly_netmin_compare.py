import sys,os,csv,numpy as np,datetime
sys.path.insert(0,'.');os.environ["LEAD_YEARS"]="continuous"
import rhizo_engine as E, run_validation_multisite as m
E.ROOT_C_REALIZED_GROWTH=True
for a in os.environ.get('OVR','').split(';'):
    if a: setattr(E,a.split('=')[0],eval(a.split('=',1)[1]))
site=sys.argv[1];N=int(sys.argv[2])
allsites=dict(m.SITES);allsites.update(m.HELDOUT_SITES)
lat,lon=allsites[site]
wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
rec=[]
import sys as _s
orig=E.sixpool_ml_step
def w(*a,**k):
    r=orig(*a,**k)
    f=_s._getframe(1);doy=None
    while f is not None and doy is None:
        ww=f.f_locals.get('w')
        if isinstance(ww,dict) and 'doy' in ww: doy=ww['doy']
        f=f.f_back
    rec.append((doy,r));return r
E.sixpool_ml_step=w
res=m.engine(site,wx,soil,cl,N,'leadin')
y0=min(wx);days=sum(366 if (y%4==0 and (y%100!=0 or y%400==0)) else 365 for y in wx)
d=f'/tmp/cycles-run15/output/{site}N{N}'
Nn=[r for r in csv.DictReader(open(d+'/dailyN.csv')) if r['date'][0]!='#']
eng=np.zeros(12);cyc=np.zeros(12);yrs=len(wx)
cum=np.cumsum([0,31,28,31,30,31,30,31,31,30,31,30,31])
miss=sum(1 for d_,_ in rec if d_ is None)
for d_,r in rec:
    if d_ is None: continue
    mth=int(np.searchsorted(cum,min(d_,365),side='left'))-1 if d_>1 else 0
    eng[max(0,mth)]+=r
for r in Nn:
    cyc[datetime.date.fromisoformat(r['date']).month-1]+=float(r['net_mineralization'])
print('MON',site,'N',N,'nodoy',miss,'calls',len(rec))
print('  Cycles',' '.join('%5.1f'%x for x in cyc/yrs),' total %.0f'%(cyc.sum()/yrs))
print('  engine',' '.join('%5.1f'%x for x in eng/yrs),' total %.0f'%(eng.sum()/yrs))
