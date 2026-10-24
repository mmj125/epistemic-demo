"""Daily growth-law attribution (REFIT_PLAN row 50): with Cycles' daily canopy, water stress, N stress and net mineralization forced into the engine,
compare the engine's daily biomass gain with Cycles' own (difference of daily total biomass). Usage: python3 growth_attrib.py NSITES N OUT.npz"""
import sys,os,csv,json,random,numpy as np
os.environ["REGIONAL"]="0";os.environ["LEAD_YEARS"]="continuous";os.environ["BIGSET"]="/tmp/w/big240.json"
NS,NN,OUT=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3];sys.argv=['x']
sys.path.insert(0,'.')
import rhizo_engine as E, run_validation_multisite as m, forcelib
from multiprocessing import Pool
ALL={}
for f in ("/tmp/w/big240.json","/tmp/w/old28.json"):ALL.update({k:tuple(v) for k,v in json.load(open(f)).items()})
random.seed(33);SITES=sorted(random.sample(sorted(ALL),NS))
KEYS=('canopy','water','wclock','nstress','nclock','netmin')
def one(site):
    lat,lon=ALL[site];N=NN
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=forcelib.force(site,N,KEYS);E.DIAG_GROWTH=[]
    r=m.engine(site,wx,soil,cl,N,'leadin');D=E.DIAG_GROWTH
    segs=[];cur=[]
    for d in D:
        if cur and d[0]<cur[-1][0]: segs.append(cur);cur=[]
        cur.append(d)
    if cur: segs.append(cur)
    ys=sorted(r)
    if len(segs)!=len(ys): return site,None
    # Cycles daily biomass
    B={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        B[x['date']]=(float(x['biomass']),float(x['radiation_interception']),float(x['water_stress']),float(x['nitrogen_stress']),float(x['temperature_factor']))
    rows=[]
    for y,sg in zip(ys,segs):
        for (doy,GR,GT,dgb) in sg:
            import datetime
            dt=(datetime.date(y,1,1)+datetime.timedelta(doy-1));k=dt.isoformat();kp=(dt-datetime.timedelta(1)).isoformat()
            if k in B and kp in B and doy in wx[y]:
                w=wx[y][doy];cb=(B[k][0]-B[kp][0])/1.0
                rows.append((y,doy,dgb*1.0,cb,GR/1000*E.NET_GROWTH_FRACTION,GT/1000*E.NET_GROWTH_FRACTION,B[k][1],B[k][2],B[k][3],B[k][4],w['solar'],(w['tx']+w['tn'])/2,w['tx'],w['rhx'],w['rhn']))
    return site,np.array(rows)
if __name__=="__main__":
    with Pool(4) as p: res=p.map(one,SITES,chunksize=1)
    ok={s:a for s,a in res if a is not None and len(a)}
    print('sites ok',len(ok),'of',len(SITES))
    np.savez(OUT,**{s:a for s,a in ok.items()})
