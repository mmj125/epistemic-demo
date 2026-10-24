"""Which site property explains the N=0 plant N overshoot? (2026-10-15) ratio = engine/Cycles plant N at harvest, N=0, per site; regress log ratio on site covariates
with leave-one-site-out error. Usage: python3 supply_covariates.py"""
import sys,os,csv,json,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, rhizo_engine as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
def one(site):
    lat,lon=S.ALL[site];N=0
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=None;r=m.engine(site,wx,soil,cl,N,'leadin')
    H={int(x['date'][:4]):float(x['total_nitrogen']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')) if x['date'][0]!='#'}
    ys=[y for y in r if y in H];c=np.mean([H[y] for y in ys]);e=np.mean([r[y]['n_uptake_kg_ha'] for y in ys])
    tm=np.mean([(w['tx']+w['tn'])/2 for y in wx for w in wx[y].values()]);pp=np.mean([sum(w['pp'] for w in wx[y].values()) for y in wx])
    s0=soil[0]
    return site,c,e,tm,pp,s0['clay'],s0['sand'],s0['soc'],lat
if __name__=="__main__":
    with Pool(4) as p: R=p.map(one,list(S.ALL))
    json.dump(R,open('/tmp/w/supply_cov.json','w'))
    names=['MAT','precip','clay0','sand0','soc0','lat']
    X=np.array([[r[3],r[4],r[5],r[6],r[7],r[8]] for r in R],float);y=np.log(np.array([r[2]/max(r[1],1) for r in R]))
    print('site-level log(engine/Cycles) mean %.2f sd %.2f'%(y.mean(),y.std()))
    for i,n in enumerate(names):print('  corr with %-7s %+.2f'%(n,np.corrcoef(X[:,i],y)[0,1]))
    from itertools import combinations
    def loo(cols):
        err=[]
        for k in range(len(y)):
            idx=[j for j in range(len(y)) if j!=k];A=np.c_[np.ones(len(idx)),X[idx][:,cols]];b=np.linalg.lstsq(A,y[idx],rcond=None)[0]
            err.append(y[k]-np.r_[1,X[k,cols]]@b)
        return np.sqrt(np.mean(np.square(err)))
    print('LOO rms of log ratio: none %.3f'%np.sqrt(np.mean((y-y.mean())**2)))
    for cols in [(i,) for i in range(6)]+list(combinations(range(6),2)):
        print('  ',[names[i] for i in cols],'%.3f'%loo(list(cols)))
