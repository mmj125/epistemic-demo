"""Drought and extreme years against county yields: is the engine's response the right shape and too large, or the wrong pattern? (2026-10-20)
For each year, per-site % deviation from the site's own linear trend (corn, 1982 to 2016); across-site correlation and regression slope of model on observed."""
import sys; sys.argv=['x']
exec(open('county_compare_2026_10_20.py').read().split('for crop,cfg in CROPS.items():\n    rows=stats')[0])
rows=stats("corn",CROPS["corn"])
def dev(r,a,yr):
    i=list(r["yrs"]).index(yr); tr=np.polyval(np.polyfit(r["yrs"],r[a],1),yr); return 100*(r[a][i]-tr)/tr
print("corn, all sites with data; deviation from own trend (%)")
print(" year  n | obs mean | engine mean (slope on obs, r) | Cycles mean (slope on obs, r)")
for yr in (1983,1988,1993,2002,2005,2011,2012):
    rr=[r for r in rows if yr in r["yrs"]]
    if len(rr)<10: continue
    o=np.array([dev(r,"o",yr) for r in rr]); e=np.array([dev(r,"e",yr) for r in rr]); c=np.array([dev(r,"c",yr) for r in rr])
    se=np.polyfit(o,e,1)[0]; sc_=np.polyfit(o,c,1)[0]
    print(f" {yr} {len(rr):3d} | {o.mean():+6.1f} | {e.mean():+6.1f} (slope {se:+.2f}, r {np.corrcoef(o,e)[0,1]:+.2f}) | {c.mean():+6.1f} (slope {sc_:+.2f}, r {np.corrcoef(o,c)[0,1]:+.2f})")
# by region for 2012 and 1988
for yr in (1988,2012):
    print(f"{yr} by longitude band:")
    for lo,hi in ((-80,-70),(-90,-80),(-97.5,-90),(-110,-97.5)):
        rr=[r for r in rows if yr in r["yrs"] and lo<=r["lon"]<hi]
        if len(rr)<3: continue
        print(f"  lon {lo} to {hi}: n={len(rr)} obs {np.mean([dev(r,'o',yr) for r in rr]):+.0f}%  engine {np.mean([dev(r,'e',yr) for r in rr]):+.0f}%  Cycles {np.mean([dev(r,'c',yr) for r in rr]):+.0f}%")
