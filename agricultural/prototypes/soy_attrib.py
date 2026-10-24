"""Soybean daily growth attribution (REFIT_PLAN row 53): fresh sites, CROPSEL=soy, N=0, Cycles' daily canopy and water stress forced into the engine; compare the engine's daily
biomass gain with Cycles' own (difference of daily total biomass) and the end-of-season totals. Usage: python3 soy_attrib.py NSITES OUT.npz"""
import sys,os,csv,json,random,datetime,numpy as np
os.environ["REGIONAL"]="0";os.environ["LEAD_YEARS"]="continuous";os.environ["BIGSET"]="/tmp/w/fresh120.json";os.environ["CROPSEL"]="soy"
NS,OUT=int(sys.argv[1]),sys.argv[2];sys.argv=['x']
sys.path.insert(0,'.')
import rhizo_engine as E, run_validation_multisite as m
from multiprocessing import Pool
ALL={k:tuple(v) for k,v in json.load(open("/tmp/w/fresh120.json")).items()}
random.seed(5);SITES=sorted(random.sample([k for k in sorted(ALL) if os.path.isdir(f'/tmp/cycles-run15/output/{k}soyN0')],NS))
def series(site):
    F={};B={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}soyN0/dailySoybeanMG.5.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        d=datetime.date.fromisoformat(x['date']);f=F.setdefault(d.year,{'canopy':{},'water':{},'wclock':{}});doy=d.timetuple().tm_yday
        f['canopy'][doy]=float(x['radiation_interception']);f['water'][doy]=1-float(x['water_stress'])/100;f['wclock'][doy]=f['water'][doy]
        B[x['date']]=(float(x['biomass']),float(x['radiation_interception']),float(x['water_stress']),float(x['temperature_factor']),float(x['grain_biomass']),float(x['aboveground_biomass']))
    return F,B
def one(site):
    lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    F,B=series(site);E.FORCE_SERIES=F;E.DIAG_GROWTH=[]
    r=m.engine(site,wx,soil,cl,0,'leadin');D=E.DIAG_GROWTH
    segs=[];cur=[]
    for d in D:
        if cur and d[0]<cur[-1][0]: segs.append(cur);cur=[]
        cur.append(d)
    if cur: segs.append(cur)
    ys=sorted(r)
    if len(segs)!=len(ys): return site,None,None
    rows=[]
    for y,sg in zip(ys,segs):
        for (doy,GR,GT,dgb) in sg:
            dt=datetime.date(y,1,1)+datetime.timedelta(doy-1);k=dt.isoformat();kp=(dt-datetime.timedelta(1)).isoformat()
            if k in B and kp in B and doy in wx[y]:
                w=wx[y][doy];rows.append((y,doy,dgb,B[k][0]-B[kp][0],GR/1000*E.NET_GROWTH_FRACTION,GT/1000*E.NET_GROWTH_FRACTION,B[k][1],B[k][2],B[k][3],w['solar'],(w['tx']+w['tn'])/2,w['tx'],w['rhx'],w['rhn']))
    H={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}soyN0/harvest.csv')):
        if x['date'][0]!='#': H[int(x['date'][:4])]=(float(x['grain_yield']),float(x['total_biomass']) if 'total_biomass' in x else np.nan)
    ends=[(y,r[y]['grain'],r[y]['total'],H[y][0],H[y][1]) for y in ys if y in H and y in r]
    return site,np.array(rows),np.array(ends)
if __name__=="__main__":
    with Pool(4) as p: res=p.map(one,SITES,chunksize=1)
    ok={s:(a,e) for s,a,e in res if a is not None and len(a)}
    print('sites ok',len(ok),'of',len(SITES))
    np.savez(OUT,**{s+'_d':v[0] for s,v in ok.items()},**{s+'_e':v[1] for s,v in ok.items()})
