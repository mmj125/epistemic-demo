"""Decompose residual grain error with all states forced (row 49): engine vs Cycles total biomass and harvest index, N=150 and N=0."""
import sys,os,csv,json,random,numpy as np
sys.argv=['x','80','/dev/null']
import force_attrib as F
E=F.E;m=F.m;forcelib=F.forcelib
def one(a):
    site,N,sub=a;lat,lon=F.ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    keys=tuple(k for b in sub for k in F.BLK[b])
    E.FORCE_SERIES=forcelib.force(site,N,keys) if keys else None
    r=m.engine(site,wx,soil,cl,N,'leadin')
    H={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')):
        if x['date'][0]=='#':continue
        H[int(x['date'][:4])]=(float(x['grain_yield']),float(x['total_biomass']))
    ys=[y for y in r if y in H]
    return site,N,sub,float(np.mean([r[y]['grain'] for y in ys])),float(np.mean([H[y][0] for y in ys])),float(np.mean([r[y]['total_biomass'] for y in ys])),float(np.mean([H[y][1] for y in ys]))
if __name__=="__main__":
    from multiprocessing import Pool
    with Pool(4) as p: res=p.map(one,[(s,N,sub) for sub in ('','CWNS') for N in (0,150) for s in F.SITES],chunksize=2)
    for N in (0,150):
        for sub in ('','CWNS'):
            q=[r for r in res if r[1]==N and r[2]==sub]
            g=np.array([[r[3],r[4]] for r in q]);b=np.array([[r[5],r[6]] for r in q])
            print('N',N,sub or 'none','grain model %.2f cycles %.2f | biomass model %.2f cycles %.2f | HI model %.3f cycles %.3f'%(g[:,0].mean(),g[:,1].mean(),b[:,0].mean(),b[:,1].mean(),g[:,0].mean()/b[:,0].mean(),g[:,1].mean()/b[:,1].mean()))
