"""Yield response to summer rainfall: observed county yield against engine and Cycles, per site (2026-10-20).
Per site: detrended yield anomaly (% of trend) regressed on the June to August precipitation anomaly (% of the site's mean), pooled slopes (% yield per % rain)."""
import sys; sys.argv=['x']; 
import os
exec(open('county_compare_2026_10_20.py').read().split('for crop,cfg in CROPS.items():\n    rows=stats')[0])
import field_data as fd
rows=stats("corn",CROPS["corn"]); S=json.load(open('sitesets/fresh94.json'))
def jja(site):
    lat,lon=S[site]; wx,_=fd.resolve_field_weather(lat,lon)
    return {y:sum(r["pp"] for d,r in days.items() if 152<=d<=243) for y,days in wx.items()}
res={"o":[],"e":[],"c":[]}; X=[]; lonv=[]
for r in rows:
    p=jja(r["site"]); pv=np.array([p[y] for y in r["yrs"]]); pa=100*(pv-pv.mean())/pv.mean()
    X.append(pa); lonv.append(np.full(len(pa),r["lon"]))
    for a in res:
        v=r[a]; tr=np.polyval(np.polyfit(r["yrs"],v,1),r["yrs"]); res[a].append(100*(v-tr)/tr)
X=np.concatenate(X); L=np.concatenate(lonv)
for lab,m in (("all sites",np.ones_like(X,bool)),("east of -90",L>-90),("-97.5 to -90",(L<=-90)&(L>-97.5)),("west of -97.5",L<=-97.5)):
    out=[]
    for a,name in (("o","observed"),("e","engine"),("c","Cycles")):
        y=np.concatenate(res[a])[m]; x=X[m]; b=np.polyfit(x,y,1); out.append(f"{name} slope {b[0]:.2f} (r {np.corrcoef(x,y)[0,1]:.2f})")
    print(f"{lab:14s} n={int(m.sum()):5d} | "+" | ".join(out))
# dry years only (JJA rain more than 20 percent below the site mean): mean yield anomaly
dry=X<-20
print("site-years with JJA rain >20% below normal:",int(dry.sum()),"| mean yield anomaly obs %.1f%% engine %.1f%% Cycles %.1f%%"%tuple(np.concatenate(res[a])[dry].mean() for a in ("o","e","c")))
wet=X>20
print("site-years with JJA rain >20% above normal:",int(wet.sum()),"| mean yield anomaly obs %.1f%% engine %.1f%% Cycles %.1f%%"%tuple(np.concatenate(res[a])[wet].mean() for a in ("o","e","c")))
