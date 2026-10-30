"""Designed Cycles runs under constant weather (2026-10-30): per-day ammonia loss against top-layer ammonium for a single fertilizer application, varying temperature, wind, soil clay and water capacity one at a time. Cycles only."""
import re,subprocess,shutil,csv,os,glob,numpy as np
CY="/tmp/cycles-run15"; BASE="f001_450_1020"
def rd(p): return [r for r in csv.DictReader(l for l in open(p) if not l.startswith('#'))]
def run(spread=0.0,rain_every=0,T=15.0,wind=3.0,clay=10.0,sand=60.0,fc=0.25,pwp=0.10,bd=1.4,rh=70.0,solar=15.0,rain=0.0,days=14):
    nm="cwv"
    # weather: constant, 1980 to 1981 (leap year handled by 366/365 rows)
    rows=["LATITUDE                45.000000","ALTITUDE                0.000000","SCREENING_HEIGHT        10.0","YEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND","####    ###     mm      deg C   deg C   MJ/m2   %       %       m/s"]
    for y in (1980,1981):
        for d in range(1,367 if y==1980 else 366): rows.append(f"{y}\t{d}\t{(5.0 if (rain_every and d%rain_every==0) else rain):.4f}\t{T+spread:.2f}\t{T-spread:.2f}\t{solar:.4f}\t{rh:.2f}\t{rh:.2f}\t{wind:.3f}")
    open(f"{CY}/input/{nm}.weather","w").write("\n".join(rows)+"\n")
    L=[l.split() for l in open(f"{CY}/input/{BASE}.soil").read().split("\n")]
    names=[r for r in L if r and r[0]=="LAYER"][0]; ic,is_,ib,ifc,ipw=[names.index(c) for c in ("CLAY","SAND","BD","FC","PWP")]
    out=[]
    for r in L:
        if r and r[0].isdigit(): r=list(r); r[ic]=str(clay); r[is_]=str(sand); r[ib]=str(bd); r[ifc]=str(fc); r[ipw]=str(pwp)
        out.append("\t".join(r))
    open(f"{CY}/input/{nm}.soil","w").write("\n".join(out))
    c=open(f"{CY}/input/{BASE}N150.ctrl").read().replace(f"{BASE}.soil",f"{nm}.soil").replace(f"{BASE}.weather",f"{nm}.weather").replace("SIMULATION_END_YEAR     2016","SIMULATION_END_YEAR     1981")
    open(f"{CY}/input/{nm}.ctrl","w").write(c)
    shutil.copy(f"{CY}/input/{BASE}N150.operation",f"{CY}/input/{nm}.operation")
    c=open(f"{CY}/input/{nm}.ctrl").read().replace(f"{BASE}N150.operation",f"{nm}.operation"); open(f"{CY}/input/{nm}.ctrl","w").write(c)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"
    N=rd(d+"dailyN.csv"); Ly=rd(d+"dailySoilLayersCN.csv"); W=rd(d+"dailyWater.csv"); shutil.rmtree(d,ignore_errors=True)
    for e in ("ctrl","soil","operation","weather"): os.remove(f"{CY}/input/{nm}.{e}")
    pnh=np.array([float(r['profile_soil_NH4']) for r in N]); j=int(np.argmax(np.diff(pnh)>50))+1
    vol=np.array([float(r['volatilization']) for r in N]); nh4=np.array([float(r['NH4.1']) for r in Ly])
    th=np.array([float(r['soil_moisture_content.1']) for r in W])
    run.theta=th[j:j+days]
    return j,vol[j:j+days],nh4[j:j+days]
if __name__=="__main__":
    print("per-day rate = loss(d) / topNH4(d-1); first 5 days; total loss over 14 days")
    def show(lbl,**kw):
        j,v,n=run(**kw); rate=v[1:6]/np.maximum(n[:5],1e-9); print(f"{lbl:34s} sum14 {v.sum():6.2f}  rate d1..d5 {np.round(rate,4).tolist()}  top NH4 d0 {n[0]:.1f}")
    for T in (5,15,25): 
        for u in (1,3,6): show(f"T {T} wind {u}",T=T,wind=u)
