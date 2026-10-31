"""Designed Cycles run (2026-10-30): effect of surface residue cover on ammonia volatilization under constant weather with enough rain for a crop. Four years, fertilizer applied each year; year-n residue comes from the crop of year n-1. Cycles only."""
import re,subprocess,shutil,csv,os,glob,numpy as np
import sys; sys.path.insert(0,'.')
import rhizo_engine as E
CY="/tmp/cycles-run15"; BASE="f001_450_1020"
def rd(p): return [r for r in csv.DictReader(l for l in open(p) if not l.startswith('#'))]
def run(fert_doy=None,T=18.0,wind=3.0,rain_every=3,rain_mm=6.0,standing=None,removed=None,clay=10.0,sand=60.0,fc=0.28,pwp=0.15,bd=1.4,years=(1980,1983)):
    nm="rsv"; rows=["LATITUDE                45.000000","ALTITUDE                0.000000","SCREENING_HEIGHT        10.0","YEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND","####    ###     mm      deg C   deg C   MJ/m2   %       %       m/s"]
    for y in range(years[0],years[1]+1):
        for d in range(1,367 if y%4==0 else 366): rows.append(f"{y}\t{d}\t{(rain_mm if d%rain_every==0 else 0.0):.4f}\t{T+6:.2f}\t{T-6:.2f}\t18.0\t80.0\t50.0\t{wind:.3f}")
    open(f"{CY}/input/{nm}.weather","w").write("\n".join(rows)+"\n")
    L=[l.split() for l in open(f"{CY}/input/{BASE}.soil").read().split("\n")]
    names=[r for r in L if r and r[0]=="LAYER"][0]; ic,is_,ib,ifc,ipw=[names.index(c) for c in ("CLAY","SAND","BD","FC","PWP")]
    out=[]
    for r in L:
        if r and r[0].isdigit(): r=list(r); r[ic]=str(clay); r[is_]=str(sand); r[ib]=str(bd); r[ifc]=str(fc); r[ipw]=str(pwp)
        out.append("\t".join(r))
    open(f"{CY}/input/{nm}.soil","w").write("\n".join(out))
    op=open(f"{CY}/input/{BASE}N150.operation").read()
    if standing is not None: op=re.sub(r"(?m)^STANDING_RESIDUE_AT_HARVEST\s+\S+",f"STANDING_RESIDUE_AT_HARVEST          {standing}",op)
    if removed is not None: op=re.sub(r"(?m)^RESIDUE_REMOVED\s+\S+",f"RESIDUE_REMOVED                     {removed}",op)
    if fert_doy is not None:
        i=op.index('FIXED_FERTILIZATION'); j=op.index('DOY',i); k=op.index('\n',j); op=op[:j]+f'DOY                                 {fert_doy}'+op[k:]
    open(f"{CY}/input/{nm}.operation","w").write(op)
    c=open(f"{CY}/input/{BASE}N150.ctrl").read().replace(f"{BASE}.soil",f"{nm}.soil").replace(f"{BASE}.weather",f"{nm}.weather").replace(f"{BASE}N150.operation",f"{nm}.operation").replace("SIMULATION_END_YEAR     2016",f"SIMULATION_END_YEAR     {years[1]}").replace("SIMULATION_START_YEAR   1980",f"SIMULATION_START_YEAR   {years[0]}")
    open(f"{CY}/input/{nm}.ctrl","w").write(c)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"
    N=rd(d+"dailyN.csv"); Ly=rd(d+"dailySoilLayersCN.csv"); W=rd(d+"dailyWater.csv"); R=rd(d+"dailyResidue.csv"); shutil.rmtree(d,ignore_errors=True)
    for e in ("ctrl","soil","operation","weather"): os.remove(f"{CY}/input/{nm}.{e}")
    pnh=np.array([float(r['profile_soil_NH4']) for r in N]); jumps=np.where(np.diff(pnh)>50)[0]+1
    h=E.saxton_rawls(sand,clay,0.5*E.OM_FROM_SOC); layer=dict(thick=0.1,sat=h["sat"],clay=clay)
    res=[]
    for j in jumps:
        vol=np.array([float(N[k]['volatilization']) for k in range(j,j+4)]); nh4=np.array([float(Ly[k]['NH4.1']) for k in range(j,j+4)]); th=np.array([float(W[k]['soil_moisture_content.1']) for k in range(j,j+4)])
        cover=float(R[j]['radiation_interception']); ag=float(R[j]['aboveground_residue_biomass'])
        pred=[]
        for k in range(1,4):
            layer["theta"]=th[k-1]; pred.append(E.volatilization_designed(nh4[k-1],layer,wind,T+6,T-6))
        res.append((N[j]['date'],ag,cover,float(np.sum(vol[1:4])/np.sum(pred))))
    return res
if __name__=="__main__":
    for lbl,kw in (("standing 50, removed 0",dict()),("standing 0, removed 0",dict(standing=0,removed=0)),("standing 100, removed 0",dict(standing=100,removed=0)),("residue removed 90",dict(removed=90))):
        print(lbl); 
        for r in run(**kw): print(f"   {r[0]}: aboveground residue {r[1]:.2f} Mg/ha, residue cover {r[2]:.2f}, obs/pred ratio {r[3]:.2f}")
