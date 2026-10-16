"""Rebuild phase 2 attribution: force Cycles' daily layer moisture into the engine (all windows) and see how much of the N=0 / N=150 error disappears.
Usage: NSITES=24 python3 water_attrib.py -> prints pooled error unforced vs forced. Uses cached Cycles reference."""
import os,sys,json,math,statistics as st
os.environ.setdefault('LEAD_YEARS','continuous'); os.environ.setdefault('CARRY_N','1')
sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, water_scorecard as W
from multiprocessing import Pool
VARS=[('grain',None),('leach','n_leached_kg_ha'),('denit','n_denitrified_kg_ha'),('volat','n_volatilized_pool_kg_ha'),('n2o','n2o_emitted_kg_ha')]
def one(args):
    site,ll=args; lat,lon=ll
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        H,A=m.run_cycles(site,N); T=W.cycles_theta(site,N)
        for force in (False,True):
            E.THETA_FORCE=T if force else None
            R=m.engine(site,wx,soil,cl,N,'leadin'); E.THETA_FORCE=None
            ys=[y for y in sorted(set(H)&set(R)) if y in A]
            row={}
            for v,ek in VARS:
                a=[H[y]['grain'] if v=='grain' else A[y][v] for y in ys]; b=[R[y]['grain'] if v=='grain' else R[y].get(ek,0.0) for y in ys]
                row[v]=(st.mean(abs(x-z) for x,z in zip(a,b)),st.mean(a))
            out[f'N{N}|{"forced" if force else "free"}']=row
    return site,out
if __name__=="__main__":
    S=json.load(open(os.environ.get('SITESET','sitesets/fresh94.json'))); ks=sorted(S); n=int(os.environ.get('NSITES','24'))
    ks=[ks[i] for i in range(0,len(ks),max(1,len(ks)//n))][:n]
    ks=[k for k in ks if all(os.path.exists(f'{m.CY}/output/{k}N{N}/dailyWater.csv') for N in (0,150))]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    json.dump(R,open('/tmp/w/water_attrib.json','w'))
    print(len(R),'sites; mean abs error free -> forced (removed %)')
    for N in (0,150):
        for v,_ in VARS:
            f=st.mean(o[f'N{N}|free'][v][0] for _,o in R); g=st.mean(o[f'N{N}|forced'][v][0] for _,o in R); ref=st.mean(o[f'N{N}|free'][v][1] for _,o in R)
            print(f'N={N} {v:6s} Cycles mean {ref:6.2f}  MAE {f:6.2f} -> {g:6.2f}  ({100*(f-g)/f:+.0f}%)')
