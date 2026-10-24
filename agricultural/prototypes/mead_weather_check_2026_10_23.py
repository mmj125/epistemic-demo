"""Engine's gridded weather against the Mead towers' own measurements, 2001 to 2016 (the engine tile ends in 2016).
Tower P columns are daily means of per-record mm, so daily mm = mean x records per day (the Mead BASE files are hourly, so 24; with 48 the annual totals reach 1400 to 1700 mm, which is impossible there)."""
import os, csv, sys; os.environ["REGIONAL"]="0"
import numpy as np, datetime as dt
import run_validation_multisite as m
SITES={"Ne1":(41.1651,-96.4766),"Ne2":(41.1649,-96.4701),"Ne3":(41.1797,-96.4397)}
def tower(site):
    rd=csv.reader(open(f"../data/ameriflux/US-{site}_daily.csv")); h=next(rd); rows=list(rd)
    def col(names):
        for n in names:
            if n in h: return h.index(n)
        raise SystemExit(f"{site}: none of {names} in header; have "+", ".join(c for c in h if c.startswith(("P","SW_IN","TA"))))
    ip=col(["P_PI_F_1_1_1","P_1_1_1"]); isw=col(["SW_IN_PI_F_1_1_1","SW_IN_1_1_1","SW_IN_F","SW_IN_1_1_2"]); ita=col(["TA_PI_F_1_1_1","TA_1_1_1"])
    out={}
    for r in rows:
        f=lambda i: float(r[i]) if i<len(r) and r[i]!="" else np.nan
        out[r[0]]=(f(ip),f(isw),f(ita))
    return out,h[ip],h[isw],h[ita]
print("site  yrs  | precip: annual tower/engine mm, daily r | solar: bias MJ/m2/d, daily r | tmean: bias C, daily r")
for site,(lat,lon) in SITES.items():
    T,np_,ns_,nt_=tower(site); wx,_=m.fd.resolve_field_weather(lat,lon)
    P=[];S=[];Tm=[]; ann=[]
    for y in range(2001,2017):
        t=[];e=[]
        for doy,d in wx[y].items():
            date=(dt.date(y,1,1)+dt.timedelta(days=doy-1)).isoformat()
            if date not in T: continue
            p,sw,ta=T[date]
            P.append((p*24.0,d["pp"])); S.append((sw*0.0864,d["solar"])); Tm.append((ta,(d["tx"]+d["tn"])/2))
    def stats(x):
        a=np.array(x); a=a[~np.isnan(a).any(1)]; return a, np.corrcoef(a[:,0],a[:,1])[0,1], (a[:,1]-a[:,0]).mean()
    p,pr,pb=stats(P); s,sr,sb=stats(S); t,tr,tb=stats(Tm)
    n=len(p)/16.0
    print(f"{site}  {len(p)/365.0:4.1f} | {p[:,0].sum()/16:5.0f}/{p[:,1].sum()/16:5.0f} r {pr:.2f} | {sb:+.2f} r {sr:.3f} | {tb:+.2f} r {tr:.3f}   [cols {np_}, {ns_}, {nt_}]")
