"""Where is the yield error? Per site-year, engine vs Cycles v1.5.20: intercepted radiation, water-stress and N-stress
multipliers (weighted by intercepted radiation), season length, biomass and grain. Writes /tmp/w/attrib_N{N}.json.
Usage: python3 yield_attribution.py N   (N = 0 | 150 | 400)"""
import sys,os,csv,json,datetime,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
import rhizo_engine as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
N=int(sys.argv[1]) if len(sys.argv)>1 else 150
ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
orig=m.simulate_continuous
def sc(*a,**k):
    k['record_history']=True;return orig(*a,**k)
m.simulate_continuous=sc
def one(site):
    lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    r=m.engine(site,wx,soil,cl,N,'leadin')
    d=f'/tmp/cycles-run15/output/{site}N{N}'
    D={}
    for x in csv.DictReader(open(d+'/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        D.setdefault(int(x['date'][:4]),{})[datetime.date.fromisoformat(x['date']).timetuple().tm_yday]=x
    H={}
    for x in csv.DictReader(open(d+'/harvest.csv')):
        if x['date'][0]=='#':continue
        H[int(x['date'][:4])]=x
    out=[]
    for y in sorted(r):
        h=r[y].get('history');cy=D.get(y)
        if not h or not cy or y not in H: continue
        sol=lambda doy: wx[y][doy]['solar']
        Ie=sum(x['canopy']*sol(x['doy']) for x in h)
        We=sum(x['canopy']*sol(x['doy'])*x['water_stress'] for x in h)/max(Ie,1e-9)
        Ne=sum(x['canopy']*sol(x['doy'])*x['n_stress'] for x in h)/max(Ie,1e-9)
        Ic=sum(float(v['radiation_interception'])*sol(doy) for doy,v in cy.items() if doy in wx[y])
        Wc=sum(float(v['radiation_interception'])*sol(doy)*(1-float(v['water_stress'])/100) for doy,v in cy.items() if doy in wx[y])/max(Ic,1e-9)
        Nc=sum(float(v['radiation_interception'])*sol(doy)*(1-float(v['nitrogen_stress'])/100) for doy,v in cy.items() if doy in wx[y])/max(Ic,1e-9)
        Bc=max(float(v['biomass']) for v in cy.values())
        out.append(dict(y=y,Ie=Ie,Ic=Ic,We=We,Wc=Wc,Ne=Ne,Nc=Nc,Le=len(h),Lc=len(cy),Be=r[y]['total'],Bc=Bc,Ge=r[y]['grain'],Gc=float(H[y]['grain_yield'])))
    return site,out
if __name__=="__main__":
    with Pool(8) as p: res=dict(p.map(one,list(ALL)))
    json.dump(res,open(f'/tmp/w/attrib_N{N}.json','w'))
    print('done',N,sum(len(v) for v in res.values()),'site-years')
