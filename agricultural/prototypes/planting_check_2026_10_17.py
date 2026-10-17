"""Planting date agreement (2026-10-17): engine (soil temperature trigger, window 110-131) vs Cycles planting_date, corn N=150, 24 fresh sites, all years."""
import os,sys,json,csv,shutil,datetime,statistics as st
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); N=150
    m._run_cycles_uncached(site,N); d=f"{CY}/output/{site}N{N}/"; P={}
    for x in csv.DictReader(open(d+"harvest.csv")):
        if x["date"][0]=="#": continue
        P[int(x["date"][:4])]=datetime.date.fromisoformat(x["planting_date"]).timetuple().tm_yday
    shutil.rmtree(d,ignore_errors=True)
    E.DIAG_STATE=[]; m.engine(site,wx,soil,cl,N,"leadin"); D=E.DIAG_STATE; E.DIAG_STATE=None
    first={}
    for (y,doy,eie,ns,pn) in D:
        if y not in first: first[y]=doy
    diffs=[first[y]-P[y] for y in first if y in P]
    return site,dict(mean=st.mean(diffs),mad=st.mean(abs(x) for x in diffs),cyc=st.mean(P[y] for y in first if y in P),eng=st.mean(first[y] for y in first if y in P),corr=m.corr([P[y] for y in first if y in P],[first[y] for y in first if y in P]))
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    for s,o in R: print(f"{s:16s} Cycles DOY {o['cyc']:5.1f} engine {o['eng']:5.1f} mean diff {o['mean']:+5.1f} mean abs {o['mad']:4.1f} yearly corr {o['corr']:.2f}")
    print("all sites: mean abs diff %.1f days, mean diff %+.1f, mean yearly corr %.2f"%(st.mean(o['mad'] for _,o in R),st.mean(o['mean'] for _,o in R),st.mean(o['corr'] for _,o in R if o['corr']==o['corr'])))
