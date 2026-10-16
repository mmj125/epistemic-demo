"""Rebuild phase 4 verification: is the crop-side N mechanism the lever? Force Cycles' daily plant N (total_nitrogen) and/or N stress in the growing season. 24 fresh sites, N=0 and 150."""
import os,sys,csv,json,datetime,statistics as st
os.environ.setdefault('LEAD_YEARS','continuous'); os.environ.setdefault('CARRY_N','1'); os.environ.setdefault('REGIONAL','0')
sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
VARS=[('grain',None),('total_biomass',None),('leach','n_leached_kg_ha'),('denit','n_denitrified_kg_ha'),('volat','n_volatilized_pool_kg_ha')]
def series(site,N):
    F={}
    for x in csv.DictReader(open(f'{m.CY}/output/{site}N{N}/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999': continue
        d=datetime.date.fromisoformat(x['date']); f=F.setdefault(d.year,{'plantn':{},'nstress':{}}); doy=d.timetuple().tm_yday
        f['plantn'][doy]=float(x['total_nitrogen']); f['nstress'][doy]=1-float(x['nitrogen_stress'])/100
    return F
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        H,A=m.run_cycles(site,N); P=series(site,N)
        for mode in ('free','plantn','nstress','both'):
            F={y:{k:v for k,v in d.items() if mode=='both' or k==mode} for y,d in P.items()}
            E.FORCE_SERIES=None if mode=='free' else F
            R=m.engine(site,wx,soil,cl,N,'leadin'); E.FORCE_SERIES=None
            ys=[y for y in sorted(set(H)&set(R)) if y in A]; row={}
            for v,ek in VARS:
                key={'grain':'grain','total_biomass':'total'}.get(v)
                x=[H[y][key] if key else A[y][v] for y in ys]; z=[R[y][key] if key else R[y].get(ek,0.0) for y in ys]
                row[v]=(st.mean(abs(i-j) for i,j in zip(x,z)),st.mean(j-i for i,j in zip(x,z)))
            out[f'N{N}|{mode}']=row
    return site,out
if __name__=="__main__":
    S=json.load(open('/tmp/w/s24.json'))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    json.dump(R,open('/tmp/w/plantn_attrib.json','w'))
    for N in (0,150):
        for v,_ in VARS:
            r={md:st.mean(o[f'N{N}|{md}'][v][0] for _,o in R) for md in ('free','plantn','nstress','both')}
            print(f'N={N} {v:13s} MAE free {r["free"]:6.2f} | +plantN {r["plantn"]:6.2f} ({100*(r["free"]-r["plantn"])/r["free"]:+.0f}%) | +Nstress {r["nstress"]:6.2f} ({100*(r["free"]-r["nstress"])/r["free"]:+.0f}%) | both {r["both"]:6.2f} ({100*(r["free"]-r["both"])/r["free"]:+.0f}%)')
