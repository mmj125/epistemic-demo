"""Rebuild phase 2 (2026-10-16): daily per-layer soil water, engine vs Cycles v1.5.20, same tile inputs.
Usage: SITESET=sitesets/fresh94.json NSITES=24 python3 water_scorecard.py   (needs /tmp/cycles-run15/output/<site>N150/dailyWater.csv)
Units: plant-available-water fraction (theta-pwp)/(fc-pwp); rms of the daily engine-minus-Cycles difference, per layer and pooled by depth class."""
import os,sys,csv,json,math,datetime,statistics as st
os.environ.setdefault('LEAD_YEARS','continuous'); os.environ.setdefault('CARRY_N','1')
sys.path.insert(0,'.')
import run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
CY=m.CY
def cycles_theta(site,N=150):
    T={}
    for r in csv.DictReader(open(f'{CY}/output/{site}N{N}/dailyWater.csv')):
        if r['date'][0]=='#': continue
        d=datetime.date.fromisoformat(r['date']); y=d.year; doy=d.timetuple().tm_yday
        T.setdefault(y,{})[doy]=[float(v) for k,v in r.items() if k.startswith('soil_moisture_content')]
    return T
def run(site_ll,N=150,force=False):
    site,(lat,lon)=site_ll
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl)
    T=cycles_theta(site,N)
    E.DIAG_THETA=[]; E.THETA_FORCE=T if force else None
    m.engine(site,wx,soil,cl,N,'leadin')
    rec=E.DIAG_THETA; E.DIAG_THETA=None; E.THETA_FORCE=None
    fcpwp=[(l['thick'],)+(lambda h:(h['fc'],h['pwp']))(m.saxton_rawls(l['sand'],l['clay'],l['soc']*m.OM_FROM_SOC)) for l in soil]
    top=[];dep=0;depth=[]
    for l in soil: dep+=l['thick']; depth.append(dep)
    out={}
    for y,doy,th in rec:
        c=T.get(y,{}).get(doy)
        if c is None: continue
        for i,(e,k) in enumerate(zip(th,c)):
            if i>=len(fcpwp): break
            _,fc,pw=fcpwp[i]; out.setdefault(i,[]).append(((e-pw)/(fc-pw),(k-pw)/(fc-pw)))
    res={}
    for i,v in out.items():
        d=[a-b for a,b in v]
        res[i]=dict(depth=depth[i],rms=math.sqrt(sum(x*x for x in d)/len(d)),bias=sum(d)/len(d),n=len(d))
    return site,name,res
if __name__=="__main__":
    S=json.load(open(os.environ.get('SITESET','sitesets/fresh94.json'))); ks=sorted(S)
    n=int(os.environ.get('NSITES','24')); ks=[ks[i] for i in range(0,len(ks),max(1,len(ks)//n))][:n]
    ks=[k for k in ks if os.path.exists(f'{CY}/output/{k}N150/dailyWater.csv')]
    with Pool(int(os.environ.get('NPROC','4'))) as p: R=p.map(run,[(k,S[k]) for k in ks])
    json.dump(R,open(os.environ.get('OUT','/tmp/w/water_scorecard.json'),'w'))
    cls={'0-0.3m':[],'0.3-0.6m':[],'0.6-1.0m':[],'>1.0m':[]}
    for site,name,res in R:
        for i,r in res.items():
            d=r['depth']; c='0-0.3m' if d<=0.3 else '0.3-0.6m' if d<=0.6 else '0.6-1.0m' if d<=1.0 else '>1.0m'; cls[c].append(r)
        print(site,name[:20],' '.join('L%d %.2f/%+.2f'%(int(i)+1,r['rms'],r['bias']) for i,r in sorted(res.items())[:6]))
    print('POOLED (rms / bias, PAW fraction):')
    for c,v in cls.items():
        if v: print(' ',c,'n=%d'%len(v),'rms mean %.3f'%st.mean(r['rms'] for r in v),'bias mean %+.3f'%st.mean(r['bias'] for r in v))
