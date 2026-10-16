"""Rebuild phase 4 attribution: force Cycles' daily profile NO3 and NH4 into the engine (all windows) and see how much N-loss / grain error disappears. NSITES=24."""
import os,sys,csv,json,datetime,statistics as st
os.environ.setdefault('LEAD_YEARS','continuous'); os.environ.setdefault('CARRY_N','1'); os.environ.setdefault('REGIONAL','0')
sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
VARS=[('grain',None),('leach','n_leached_kg_ha'),('denit','n_denitrified_kg_ha'),('volat','n_volatilized_pool_kg_ha'),('n2o','n2o_emitted_kg_ha')]
def pools(site,N):
    F={}
    for r in csv.DictReader(open(f'{m.CY}/output/{site}N{N}/dailyN.csv')):
        if r['date'][0]=='#': continue
        d=datetime.date.fromisoformat(r['date']); F.setdefault(d.year,{})[d.timetuple().tm_yday]=(float(r['profile_soil_NO3']),float(r['profile_soil_NH4']))
    return F
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        H,A=m.run_cycles(site,N); P=pools(site,N)
        for force in (False,True):
            E.NPOOL_FORCE=P if force else None
            R=m.engine(site,wx,soil,cl,N,'leadin'); E.NPOOL_FORCE=None
            ys=[y for y in sorted(set(H)&set(R)) if y in A]; row={}
            for v,ek in VARS:
                x=[H[y]['grain'] if v=='grain' else A[y][v] for y in ys]; z=[R[y]['grain'] if v=='grain' else R[y].get(ek,0.0) for y in ys]
                row[v]=(st.mean(abs(i-j) for i,j in zip(x,z)),st.mean(x))
            out[f'N{N}|{"forced" if force else "free"}']=row
    return site,out
if __name__=="__main__":
    S=json.load(open('/tmp/w/s24.json'))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    json.dump(R,open('/tmp/w/npool_attrib.json','w'))
    for N in (0,150):
        for v,_ in VARS:
            f=st.mean(o[f'N{N}|free'][v][0] for _,o in R); g=st.mean(o[f'N{N}|forced'][v][0] for _,o in R); ref=st.mean(o[f'N{N}|free'][v][1] for _,o in R)
            print(f'N={N} {v:6s} Cycles mean {ref:6.2f}  MAE {f:6.2f} -> {g:6.2f}  ({100*(f-g)/f:+.0f}%)')
