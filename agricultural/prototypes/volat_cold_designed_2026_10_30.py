"""Designed Cycles runs (2026-10-30): ammonia loss at and below freezing, with and without snow cover, fertilizer applied on an absolute day. Cycles only."""
import re,subprocess,shutil,csv,os,numpy as np
CY="/tmp/cycles-run15"; BASE="f001_450_1020"
def rd(p): return [r for r in csv.DictReader(l for l in open(p) if not l.startswith('#'))]
def run(T=15.0,spread=0.0,wind=3.0,precip_every=0,precip_mm=5.0,fert_doy=40,clay=10.0,sand=60.0,fc=0.28,pwp=0.15,bd=1.4,days=10):
    nm="cdv"; rows=["LATITUDE                45.000000","ALTITUDE                0.000000","SCREENING_HEIGHT        10.0","YEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND","####    ###     mm      deg C   deg C   MJ/m2   %       %       m/s"]
    for y in (1980,1981):
        for d in range(1,367 if y==1980 else 366): rows.append(f"{y}\t{d}\t{(precip_mm if precip_every and d%precip_every==0 else 0.0):.4f}\t{T+spread:.2f}\t{T-spread:.2f}\t10.0\t70.0\t70.0\t{wind:.3f}")
    open(f"{CY}/input/{nm}.weather","w").write("\n".join(rows)+"\n")
    L=[l.split() for l in open(f"{CY}/input/{BASE}.soil").read().split("\n")]
    names=[r for r in L if r and r[0]=="LAYER"][0]; ic,is_,ib,ifc,ipw=[names.index(c) for c in ("CLAY","SAND","BD","FC","PWP")]
    out=[]
    for r in L:
        if r and r[0].isdigit(): r=list(r); r[ic]=str(clay); r[is_]=str(sand); r[ib]=str(bd); r[ifc]=str(fc); r[ipw]=str(pwp)
        out.append("\t".join(r))
    open(f"{CY}/input/{nm}.soil","w").write("\n".join(out))
    op=open(f"{CY}/input/{BASE}N150.operation").read(); i=op.index('FIXED_FERTILIZATION'); j=op.index('DOY',i); k=op.index('\n',j); op=op[:j]+f'DOY                                 {fert_doy}'+op[k:]
    open(f"{CY}/input/{nm}.operation","w").write(op)
    c=open(f"{CY}/input/{BASE}N150.ctrl").read().replace(f"{BASE}.soil",f"{nm}.soil").replace(f"{BASE}.weather",f"{nm}.weather").replace(f"{BASE}N150.operation",f"{nm}.operation").replace("SIMULATION_END_YEAR     2016","SIMULATION_END_YEAR     1980")
    open(f"{CY}/input/{nm}.ctrl","w").write(c)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"
    N=rd(d+"dailyN.csv"); Ly=rd(d+"dailySoilLayersCN.csv"); W=rd(d+"dailyWater.csv"); R=rd(d+"dailyResidue.csv"); import glob; cf=[f for f in glob.glob(d+'daily*.csv') if 'Corn' in f]; C=rd(cf[0]) if cf else None; shutil.rmtree(d,ignore_errors=True)
    for e in ("ctrl","soil","operation","weather"): os.remove(f"{CY}/input/{nm}.{e}")
    pnh=np.array([float(r['profile_soil_NH4']) for r in N]); j=int(np.argmax(np.diff(pnh)>50))+1
    vol=np.array([float(N[q]['volatilization']) for q in range(j,j+days)]); nh4=np.array([float(Ly[q]['NH4.1']) for q in range(j,j+days)]); th=np.array([float(W[q]['soil_moisture_content.1']) for q in range(j,j+days)])
    run.canopy=float(C[j+1]['radiation_interception']) if C and C[j+1]['radiation_interception'] not in ('-999','') else 0.0
    run.residue=float(R[j]['aboveground_residue_biomass']); run.cover=float(R[j]['radiation_interception'])
    return vol,nh4,th
def rate(**kw):
    vol,nh4,th=run(**kw); return float(np.mean(vol[1:4]/np.maximum(nh4[:3],1e-9))), float(th[1:4].mean()), float(nh4[0])
if __name__=="__main__":
    ref15,th15,_=rate(T=15.0)
    arr=lambda T: np.exp(9641*(1/288.15-1/(T+273.15)))
    print("rate (per day, days 1-3 after application) against the Arrhenius prediction from the 15 C reference (theta-corrected)")
    for lbl,kw in (("T 15 (ref)",dict(T=15.0)),("T 5 dry",dict(T=5.0)),("T 0 dry",dict(T=0.0)),("T -1 dry",dict(T=-1.0)),("T -5 dry",dict(T=-5.0)),("T -10 dry",dict(T=-10.0)),("T -5 snow (5 mm / 3 d)",dict(T=-5.0,precip_every=3)),("T -10 snow",dict(T=-10.0,precip_every=3)),("T 2 rain (5 mm / 3 d)",dict(T=2.0,precip_every=3)),("T 2 dry",dict(T=2.0))):
        r,th,n=rate(**kw); pred=ref15*arr(kw['T'])*th15/th
        print(f"  {lbl:26s} rate {r:.5f}  theta1 {th:.3f}  topNH4 {n:.1f}  Arrhenius+theta prediction {pred:.5f}  obs/pred {r/pred if pred>0 else float('nan'):.2f}")
