"""Hydrology option audit (2026-10-16): per-year agreement of the engine with Cycles run at HYDROLOGY_OPTION 1 (hourly, the reference) and 0 (daily cascade).
Corn N=150, 12 fresh sites. For each variable: within-site yearly correlation engine-vs-opt1, engine-vs-opt0, opt0-vs-opt1, and mean levels."""
import os,sys,re,json,shutil,statistics as st
os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY
VARS=(("grain","grain",None),("leach","n_leached_kg_ha","leach"),("denit","n_denitrified_kg_ha","denit"),("volat","n_volatilized_pool_kg_ha","volat"),("n2o","n2o_emitted_kg_ha","n2o"))
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl)
    H1,A1=m.run_cycles(site,150)
    fs=site+"h0"; m.write_inputs(fs,lat,lon,wx,soil,cl)
    p=f"{CY}/input/{fs}N150.ctrl"; t=open(p).read(); open(p,"w").write(re.sub(r"^(HYDROLOGY_OPTION\s+)\S+",r"\g<1>0",t,flags=re.M))
    H0,A0=m._run_cycles_uncached(fs,150); shutil.rmtree(f"{CY}/output/{fs}N150",ignore_errors=True)
    E=m.engine(site,wx,soil,cl,150,"leadin")
    out={}
    for v,ek,ak in VARS:
        ys=[y for y in sorted(E) if y in H1 and y in H0 and (ak is None or (y in A1 and y in A0))]
        g1=lambda y:H1[y]["grain"] if ak is None else A1[y][ak]
        g0=lambda y:H0[y]["grain"] if ak is None else A0[y][ak]
        e=[E[y].get(ek,0.0) if ak else E[y]["grain"] for y in ys]
        if ak=="leach": pass
        a1=[g1(y) for y in ys]; a0=[g0(y) for y in ys]
        out[v]=dict(e=st.mean(e),o1=st.mean(a1),o0=st.mean(a0),c_e1=m.corr(e,a1),c_e0=m.corr(e,a0),c_01=m.corr(a0,a1),n=len(ys))
    return site,out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json")); ks=sorted(S)[::2]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    json.dump(R,open("scorecards/2026-10-16_hydro_audit_yearly.json","w"))
    nz=lambda x:[v for v in x if v==v]
    for v,_,_ in VARS:
        o=[r[v] for _,r in R]
        print(f"{v:6s} mean engine {st.mean(x['e'] for x in o):6.2f} opt1 {st.mean(x['o1'] for x in o):6.2f} opt0 {st.mean(x['o0'] for x in o):6.2f} | within-site yearly corr: engine~opt1 {st.mean(nz([x['c_e1'] for x in o])):.2f}  engine~opt0 {st.mean(nz([x['c_e0'] for x in o])):.2f}  opt0~opt1 {st.mean(nz([x['c_01'] for x in o])):.2f}")
