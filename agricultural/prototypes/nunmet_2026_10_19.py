"""Immobilization the engine's mineral pool could not supply (N created by the floor in apply_net_min), corn, 24 sites, continuous chain, per year from 1982, N=0 and 150."""
import os,sys,json
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]=os.environ.get("NLEV","0"); sys.path.insert(0,'.')
NLEV=int(os.environ.get("NLEV","0"))
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    E.N_UNMET=[]; m.engine(site,wx,soil,cl,NLEV,'leadin'); U=E.N_UNMET; E.N_UNMET=None
    yrs=sorted(set(y for y,_,_ in U if y is not None and y>=1982)); tot=sum(n for y,_,n in U if y is not None and y>=1982)
    return site,tot/max(1,len([y for y in range(1982,2017)])),[(d,n) for y,d,n in U if y is not None and y>=1982]
if __name__=="__main__":
    R=Pool(4).map(one,sorted(S)); a=np.array([r[1] for r in R]); print('N=%d: mean unmet immobilization %.2f kg N/ha/yr (min %.2f max %.2f)'%(NLEV,a.mean(),a.min(),a.max()))
    doys=np.array([d for r in R for d,n in r[2] if d is not None]); ns=np.array([n for r in R for d,n in r[2] if d is not None])
    for lo,hi in ((1,60),(60,120),(120,180),(180,240),(240,300),(300,367)): print(f'  doy {lo}-{hi}: {ns[(doys>=lo)&(doys<hi)].sum()/(24*35):.2f} kg/ha/yr')
