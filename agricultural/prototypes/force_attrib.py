"""State-swap attribution on random sites (REFIT_PLAN row 49). Force subsets of the engine's daily states to Cycles' own values and read the grain MAE that remains.
C canopy interception, W water stress (+clock), N nitrogen stress (+clock), S net mineralization (soil N supply). REGIONAL off, continuous chain.
Usage: python3 force_attrib.py NSITES OUT.json"""
import sys,os,csv,json,random,numpy as np
os.environ["REGIONAL"]="0";os.environ["LEAD_YEARS"]="continuous";os.environ["BIGSET"]="/tmp/w/big240.json"
NS,OUT=int(sys.argv[1]),sys.argv[2];sys.argv=['x']
sys.path.insert(0,'.')
import cycles_engine_validate as E, run_validation_multisite as m, forcelib
from multiprocessing import Pool
ALL={}
for f in ("/tmp/w/big240.json","/tmp/w/old28.json"):ALL.update({k:tuple(v) for k,v in json.load(open(f)).items()})
random.seed(21);_ok=[k for k in sorted(ALL) if os.path.isdir(f'/tmp/cycles-run15/output/{k}N400')];SITES=sorted(random.sample(_ok,NS))
NL=tuple(int(x) for x in os.environ.get('NLIST','0,150').split(','))
BLK={'C':('canopy',),'W':('water','wclock'),'N':('nstress','nclock'),'S':('netmin',)}
SUBS=os.environ.get('SUBS','').split(',') if os.environ.get('SUBS') is not None and 'SUBS' in os.environ else ['','C','W','N','S','CN','CWN','CWNS']
def one(a):
    site,N,sub=a;lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    keys=tuple(k for b in sub for k in BLK[b])
    E.FORCE_SERIES=forcelib.force(site,N,keys) if keys else None
    r=m.engine(site,wx,soil,cl,N,'leadin')
    H={int(x['date'][:4]):float(x['grain_yield']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')) if x['date'][0]!='#'}
    ys=[y for y in r if y in H];a_=np.array([H[y] for y in ys]);b=np.array([r[y]['grain'] for y in ys])
    return site,N,sub,float(np.abs(a_-b).mean()),float((b-a_).mean()),float(np.corrcoef(a_,b)[0,1]) if a_.std()>0 and b.std()>0 else 0.0
if __name__=="__main__":
    with Pool(4) as p: res=p.map(one,[(s,N,sub) for sub in SUBS for N in NL for s in SITES],chunksize=2)
    json.dump(res,open(OUT,'w'))
    for N in NL:
        base=np.mean([r[3] for r in res if r[1]==N and r[2]==''])
        print('N',N)
        for sub in SUBS:
            v=np.mean([r[3] for r in res if r[1]==N and r[2]==sub]);b=np.mean([r[4] for r in res if r[1]==N and r[2]==sub]);c=np.mean([r[5] for r in res if r[1]==N and r[2]==sub])
            print('  %-5s MAE %.3f (%3d%% of base removed) bias %+.2f corr %.2f'%(sub or 'none',v,round(100*(base-v)/base),b,c))
