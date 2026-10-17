"""Corn canopy diagnostic (2026-10-17): free engine (measured corn N config via ENGINE_OVR) vs Cycles v1.5.20 daily radiation_interception, 24 sites, continuous chain.
Per site-year: peak, season integral, day canopy first >0.5 (rise), day it last >0.5 (fall), and mean N stress multiplier (Cycles vs engine) over the season, so the canopy gap can be split
into level, timing and N-stress coupling. Usage: ENGINE_OVR=... python3 corn_canopy_diag_2026_10_17.py"""
import os,sys,json,shutil,csv,datetime,subprocess,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def summ(c):  # c: {doy:(canopy,nst)}
    d=sorted(c); cv=[c[k][0] for k in d]; ns=[c[k][1] for k in d]
    up=next((k for k in d if c[k][0]>0.5),None); dn=next((k for k in reversed(d) if c[k][0]>0.5),None)
    return dict(peak=max(cv),integ=sum(cv),up=up,dn=dn,ns=st.mean(ns),nsmin=min(ns),n=len(d))
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (0,150):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"
        C={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999':continue
            dt=datetime.date.fromisoformat(x['date']); C.setdefault(dt.year,{})[dt.timetuple().tm_yday]=(float(x['radiation_interception']),1-float(x['nitrogen_stress'])/100)
        shutil.rmtree(d,ignore_errors=True)
        E.DIAG_STATE=[]; R=m.engine(site,wx,soil,cl,N,"leadin"); S=E.DIAG_STATE; E.DIAG_STATE=None
        Ey={}
        for y,doy,eie,ns,pn in S: Ey.setdefault(y,{})[doy]=(eie,ns)
        for y in sorted(set(C)&set(Ey)):
            if len(C[y])<30 or len(Ey[y])<30: continue
            cm=set(C[y])&set(Ey[y]); out.append(dict(site=site,N=N,y=y,cy=summ(C[y]),en=summ(Ey[y]),gr=R[y]["grain"] if y in R else None,se=sum((C[y][k][0]-Ey[y][k][0])**2 for k in cm),nn=len(cm)))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    json.dump(R,open("scorecards/2026-10-17_corn_canopy_diag_24sites.json","w"))
    for N in (0,150):
        _q=[x for x in R if x['N']==N]; print(f'N={N} daily canopy rms on matched days {(sum(x["se"] for x in _q)/sum(x["nn"] for x in _q))**.5:.4f}')
        r=[x for x in R if x["N"]==N and x["cy"]["up"] and x["en"]["up"] and x["cy"]["dn"] and x["en"]["dn"]]
        g=lambda f:[f(x) for x in r]
        print(f"N={N} site-years {len(r)}")
        for k in ("peak","integ","up","dn","ns"):
            d=g(lambda x:x["en"][k]-x["cy"][k]); print(f"  engine-Cycles {k:6s} mean {st.mean(d):+.3f} sd {st.pstdev(d):.3f} (Cycles mean {st.mean(g(lambda x:x['cy'][k])):.3f})")
        di=g(lambda x:x["en"]["integ"]-x["cy"]["integ"]); dn=g(lambda x:x["cy"]["ns"]); en=g(lambda x:x["en"]["ns"])
        def cor(a,b):
            ma,mb=st.mean(a),st.mean(b); return sum((p-ma)*(q-mb) for p,q in zip(a,b))/((sum((p-ma)**2 for p in a)*sum((q-mb)**2 for q in b))**.5)
        print(f"  corr(integral gap, Cycles meanNmult) {cor(di,dn):+.2f}; corr(integral gap, engine meanNmult) {cor(di,en):+.2f}; corr(integral gap, Cycles-engine Nmult) {cor(di,[a-b for a,b in zip(dn,en)]):+.2f}")
        di_up=g(lambda x:x["en"]["up"]-x["cy"]["up"]); di_dn=g(lambda x:x["en"]["dn"]-x["cy"]["dn"])
        print(f"  corr(integral gap, rise-timing gap) {cor(di,di_up):+.2f}; corr(integral gap, fall-timing gap) {cor(di,di_dn):+.2f}")
        # split by Cycles N stress severity
        for lo,hi in ((0.9,1.01),(0.6,0.9),(0,0.6)):
            q=[x for x in r if lo<=x["cy"]["ns"]<hi]
            if q: print(f"  Cycles meanNmult in [{lo},{hi}): n={len(q)} integral gap {st.mean(x['en']['integ']-x['cy']['integ'] for x in q):+.1f} (Cycles {st.mean(x['cy']['integ'] for x in q):.1f}), engine Nmult {st.mean(x['en']['ns'] for x in q):.2f} vs Cycles {st.mean(x['cy']['ns'] for x in q):.2f}")
