"""APEX/EPIC denitrification (Kemanian and Williams, CEAP 2011 APEX model upgrades, Eqs 1 to 4) against Cycles' daily layer-1 denitrification.
Rdn = rho dz Rmax fNO3 fresp fw; Rmax 32e-6 kg N/kg soil/d; fNO3 = NO3/(NO3+60) (mg N/kg); fw = 1/(1+((1-Av)/(0.90+0.1 fclay))^-60) with Av the air-filled
volume (m3/m3); fresp = min(1, CO2/50), CO2 in mg C/kg soil/d. As published (no free parameters) and with one free amplitude. Odd/even site hold-out."""
import sys,numpy as np
sys.path.insert(0,'.')
import denit_mgmt_eval_2026_10_21 as V
import cycles_engine_validate as E
D=V.load("base"); prev=V.prev
sat=D["sat_1"]; th=prev(D["th_1"]); dz=D["thick_1"]; y=D["denit"]
bd=np.vectorize(E.sixpool_bulk_density)(sat)
c=prev(D["no3_1"])                                   # mg N/kg, start of day
resp_kg=(D["resp_som"]+D["resp_res"])*1000.0         # kg C/ha/d
soil_kg_ha=bd*dz*1e7
co2=resp_kg*1e6/soil_kg_ha                            # mg C/kg soil/d
Av=np.clip(sat-th,0,None)
same=np.zeros(len(sat),bool); same[1:]=(D["site"][1:]==D["site"][:-1])&((D["yeardoy"][1:]-D["yeardoy"][:-1]==1)|((D["yeardoy"][1:]%1000==1)&(D["yeardoy"][:-1]%1000>=365)))
m0=same&((D["yeardoy"]//1000)>=1983); site=D["site"].astype(int); odd=site%2==1; even=~odd
def r2(pred,msk): return 1-((y-pred)[msk]**2).sum()/((y[msk]-y[msk].mean())**2).sum()
def law(fclay=0.25,thr=60.0,half=60.0,cresp=50.0,expo=60.0):
    fw=1/(1+((1-Av)/(0.90+0.1*fclay))**(-expo))
    return soil_kg_ha*32e-6*(c/(c+half))*np.minimum(1.0,co2/cresp)*fw
print("median denit kg/ha/d",np.median(y[m0]),"median co2 mg/kg",np.median(co2[m0]),"median Av",np.median(Av[m0]))
yr=(D["yeardoy"]//1000).astype(int)
def annual(p,msk): n=len(set(zip(site[msk],yr[msk]))); return p[msk].sum()/n
for fc in (0.1,0.25,0.4):
    p=law(fclay=fc); a=(p[m0&odd]*y[m0&odd]).sum()/max((p[m0&odd]**2).sum(),1e-30)
    print(f"fclay {fc}: as published  R2 even {r2(p,m0&even):7.3f} annual Cycles {annual(y,m0&even):.1f} law {annual(p,m0&even):.1f} | one amplitude x{a:.3g}: R2 even {r2(a*p,m0&even):.3f} annual {annual(a*p,m0&even):.1f}")
# which factor limits: hard look at the moisture threshold on Cycles' states
print("--- moisture: mean Cycles denit by saturation bin vs mean law (fclay 0.25)")
S=th/sat
p=law()
for lo in np.arange(0.5,1.05,0.05):
    m=m0&(S>=lo)&(S<lo+0.05)
    if m.sum()>30: print(f" S {lo:.2f}-{lo+0.05:.2f} n {m.sum():6d} Cycles {y[m].mean():.4f} law {p[m].mean():.4f}")

print("--- which moisture state does the published fw need? (as published, fclay 0.25 and 0.35; R2 on even sites, annual Cycles 16.5)")
th_end=D["th_1"]; th_start=prev(D["th_1"])
states={"start of day (previous end)":th_start,"end of day":th_end,"mean of start and end":0.5*(th_start+th_end),"max of start and end":np.maximum(th_start,th_end)}
for nm,t in states.items():
    for fc in (0.25,0.35):
        Av_=np.clip(sat-t,0,None)
        fw=1/(1+((1-Av_)/(0.90+0.1*fc))**(-60.0))
        p=soil_kg_ha*32e-6*(c/(c+60.0))*np.minimum(1.0,co2/50.0)*fw
        a=(p[m0&odd]*y[m0&odd]).sum()/max((p[m0&odd]**2).sum(),1e-30)
        print(f" {nm:30s} fclay {fc}: R2 {r2(p,m0&even):.3f} annual {annual(p,m0&even):5.1f} | best amplitude x{a:.2f} R2 {r2(a*p,m0&even):.3f}")
