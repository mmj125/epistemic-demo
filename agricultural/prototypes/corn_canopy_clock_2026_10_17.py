"""Corn canopy fall-timing diagnostic (2026-10-17): in Cycles v1.5.20 output (24 sites, N=150), is the day canopy last exceeds 0.5 set by thermal time alone, or does stress shift it?
Reports Cycles thermal time at that day, its spread, and its regression on mean water and N stress multipliers over the season. Usage: python3 corn_canopy_clock_2026_10_17.py"""
import os,sys,json,shutil,csv,datetime,subprocess,statistics as st
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl)
    subprocess.run(["./Cycles",f"{site}N150"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N150/"
    Y={}
    for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        dt=datetime.date.fromisoformat(x['date']); Y.setdefault(dt.year,[]).append((dt.timetuple().tm_yday,float(x['radiation_interception']),float(x['thermal_time']),1-float(x['water_stress'])/100,1-float(x['nitrogen_stress'])/100,x['stage'] if 'stage' in x else ''))
    shutil.rmtree(d,ignore_errors=True); out=[]
    for y,L in Y.items():
        if len(L)<30: continue
        hi=[r for r in L if r[1]>0.5]
        if not hi: continue
        f=hi[-1]; u=hi[0]; pk=max(L,key=lambda r:r[1]); post=[r for r in L if r[0]>=pk[0]]
        out.append(dict(site=site,y=y,tt_dn=f[2],tt_up=u[2],tt_end=L[-1][2],tt_pk=pk[2],w=st.mean(r[3] for r in post),n=st.mean(r[4] for r in post),wall=st.mean(r[3] for r in L),dn=f[0],endd=L[-1][0]))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    json.dump(R,open("scorecards/2026-10-17_corn_canopy_clock_24sites.json","w"))
    for k in ("tt_up","tt_pk","tt_dn","tt_end"):
        v=[r[k] for r in R]; print(f"{k}: mean {st.mean(v):.0f} sd {st.pstdev(v):.0f}")
    import numpy as np
    X=np.array([[1,r["w"],r["n"]] for r in R]); y=np.array([r["tt_dn"] for r in R]); b=np.linalg.lstsq(X,y,rcond=None)[0]
    res=y-X@b; print("tt_dn ~ 1 + post-peak water mult + N mult: coef",b.round(0),"R2",round(1-res.var()/y.var(),2))
    for k in ("w","n"): print(k,"corr with tt_dn",round(float(np.corrcoef([r[k] for r in R],y)[0,1]),2))
