"""Engine yield response to elevated CO2 against FACE (Ainsworth and Long 2021, Table 1), 2026-10-27.
Constant CO2 of CO2_LO (default 390 ppm, FACE ambient) and CO2_HI (550) over every year, N=150, 24-site quick set; response = yield(HI)/yield(LO) - 1.
Site-years are split into dry and wet thirds by the low-CO2 yield relative to the site's own 90th percentile (water is the main year-to-year driver of yield).
Usage: CROPSEL=corn|sorghum|silage WEXP=0.197 REXP=0 python3 co2_face_2026_10_27.py"""
import os,sys,json
os.environ["REGIONAL"]="0"; os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"
sys.path.insert(0,'.')
import numpy as np
from multiprocessing import Pool
import run_validation_multisite as m, rhizo_engine as E
LO=float(os.environ.get("CO2_LO","390")); HI=float(os.environ.get("CO2_HI","550"))
E.WUE_CO2_EXP=float(os.environ.get("WEXP",E.WUE_CO2_EXP)); E.RUE_CO2_EXP=float(os.environ.get("REXP",E.RUE_CO2_EXP))
S=json.load(open('/tmp/w/s24.json'))
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    out={}
    for tag,c in (("lo",LO),("hi",HI)):
        E.CO2_PPM_BY_YEAR={y:c for y in range(1980,2017)}
        res=m.engine(site,wx,soil,cl,150,'leadin')
        out[tag]={y:res[y]['forage' if os.environ.get("CROPSEL")=="silage" else 'grain'] for y in res if y>1981}
    return site,lon,out
if __name__=="__main__":
    with Pool(4) as p: R=p.map(one,sorted(S))
    rows=[]
    for site,lon,o in R:
        ys=sorted(set(o["lo"])&set(o["hi"])); lo=np.array([o["lo"][y] for y in ys]); hi=np.array([o["hi"][y] for y in ys])
        ref=np.percentile(lo,90); rel=lo/ref
        for a,b,r in zip(lo,hi,rel): rows.append((lon,a,b,r))
    A=np.array(rows); ok=A[:,1]>0.3
    A=A[ok]; resp=A[:,2]/A[:,1]-1
    q=np.quantile(A[:,3],[1/3,2/3]); dry=A[:,3]<=q[0]; wet=A[:,3]>=q[1]
    west=A[:,0]<=-97.5
    bins=[(0,0.5),(0.5,0.7),(0.7,0.85),(0.85,2)]
    bs=" | ".join(f"yield {a:.2f}-{b:.2f} of ref: {100*resp[(A[:,3]>=a)&(A[:,3]<b)].mean():+.1f}% (n={((A[:,3]>=a)&(A[:,3]<b)).sum()})" for a,b in bins)
    print(f"{os.environ.get('CROPSEL','corn')} WEXP {E.WUE_CO2_EXP} REXP {E.RUE_CO2_EXP} {LO:.0f}->{HI:.0f} ppm: all {100*resp.mean():+.1f}% (mean of ratios {100*(A[:,2].mean()/A[:,1].mean()-1):+.1f}%) | dry third {100*resp[dry].mean():+.1f}% | wet third {100*resp[wet].mean():+.1f}% | west {100*resp[west].mean():+.1f}% east {100*resp[~west].mean():+.1f}%")
    print("   by relative yield:",bs)
