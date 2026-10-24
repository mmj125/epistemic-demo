import sys,os,csv,numpy as np,datetime,json
sys.path.insert(0,'.');os.environ["LEAD_YEARS"]="continuous"
import rhizo_engine as E, run_validation_multisite as m
E.ROOT_C_REALIZED_GROWTH=True
for a in os.environ.get('OVR','').split(';'):
    if a: setattr(E,a.split('=')[0],eval(a.split('=',1)[1]))
site=sys.argv[1];N=0
allsites=dict(m.SITES);allsites.update(m.HELDOUT_SITES)
lat,lon=allsites[site]
wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
rec=[];orig=E.sixpool_ml_step
def w(*a,**k):
    E.SIXPOOL_DIAG=[]
    r=orig(*a,**k);D=E.SIXPOOL_DIAG
    t0=sum(x[0]+x[10] for x in D);t1=sum(x[8] for x in D);t2=sum(x[1]-x[8] for x in D)
    f=sys._getframe(1);doy=None
    while f is not None and doy is None:
        ww=f.f_locals.get('w')
        if isinstance(ww,dict) and 'doy' in ww: doy=ww['doy']
        f=f.f_back
    rec.append((doy,t0,t1,t2,r));return r
E.sixpool_ml_step=w
m.engine(site,wx,soil,cl,N,'leadin')
yrs=len(wx);cum=np.cumsum([0,31,28,31,30,31,30,31,31,30,31,30,31])
def mon(d): return 0 if d<=1 else int(np.searchsorted(cum,min(d,365),side='left'))-1
eng=np.zeros((12,4))
for d,t0,t1,t2,r in rec:
    eng[mon(d)]+=[t0,t1,t2,r]
cy=np.zeros((12,3))
for r in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N0/dailyN.csv')):
    if r['date'][0]=='#':continue
    cy[datetime.date.fromisoformat(r['date']).month-1]+=[float(r['mineralization']),float(r['immobilization']),float(r['net_mineralization'])]
json.dump(dict(eng=(eng/yrs).tolist(),cy=(cy/yrs).tolist()),open(f'/tmp/w/mt_{site}_{os.environ.get("TAG","d")}.json','w'))
print(site,'done')
