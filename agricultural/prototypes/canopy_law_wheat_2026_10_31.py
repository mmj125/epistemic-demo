"""Designed Cycles run (2026-10-31), winter wheat: does the unstressed canopy follow Eq. 6 with 6, -20, -16, 15 on TTf = thermal time / (thermal time at maturity - emergence), half a day back?
Annual weather repeated every year (sinusoidal temperature, 4 mm rain a day), N 150, fall planting from the wheat harness operation template. Cycles only."""
import re,subprocess,shutil,csv,os,sys,numpy as np
from scipy.optimize import least_squares
sys.path.insert(0,'.')
import run_validation_multisite_wheat as W
CY="/tmp/cycles-run15"; BASE="f001_450_1020"
def rd(p): return [r for r in csv.DictReader(l for l in open(p) if not l.startswith('#'))]
def run(NN=400.0,Tmean=10.0,Tamp=13.0,rain=4.0,nyears=6,plant_doy=289):
    nm="cldw"; rows=["LATITUDE                42.000000","ALTITUDE                0.000000","SCREENING_HEIGHT        10.0","YEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND","####    ###     mm      deg C   deg C   MJ/m2   %       %       m/s"]
    for y in range(1980,1980+nyears):
        for d in range(1,366):
            T=Tmean+Tamp*np.sin(2*np.pi*(d-110)/365.0); S=14+9*np.sin(2*np.pi*(d-80)/365.0)
            rows.append(f"{y}\t{d}\t{rain:.4f}\t{T+6:.2f}\t{T-6:.2f}\t{S:.3f}\t75.00\t75.00\t2.000")
    open(f"{CY}/input/{nm}.weather","w").write("\n".join(rows)+"\n")
    shutil.copy(f"{CY}/input/{BASE}.soil",f"{CY}/input/{nm}.soil")
    c=open(f"{CY}/input/{BASE}N150.ctrl").read().replace(f"{BASE}N150.operation",f"{nm}.operation").replace(f"{BASE}.soil",f"{nm}.soil").replace(f"{BASE}.weather",f"{nm}.weather").replace("SIMULATION_END_YEAR     2016",f"SIMULATION_END_YEAR     {1980+nyears-1}")
    open(f"{CY}/input/{nm}.ctrl","w").write(c)
    op=W.OP+W.fert_text(NN); op=op.replace("DOY                                 %d"%0,"")
    open(f"{CY}/input/{nm}.operation","w").write(op)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"
    f=[x for x in os.listdir(d) if x.startswith("daily") and "Wheat" in x][0]; D=rd(d+f); shutil.rmtree(d,ignore_errors=True)
    for e in ("ctrl","soil","operation","weather"): os.remove(f"{CY}/input/{nm}.{e}")
    return D
if __name__=="__main__":
    D=run(); print(len(D),D[0].keys() if D else None)
    seas={}
    for r in D:
        if r['biomass']=='-999' or r['crop']=='FALLOW': continue
        seas.setdefault(r['date'][:4],[]).append(r)
    for y,rs in seas.items():
        TT=np.array([float(r['thermal_time']) for r in rs]); e=np.array([float(r['radiation_interception']) for r in rs]); st=[r['stage'] for r in rs]
        print(y,"days",len(rs),"TT end",TT.max(),"peak",e.max().round(3),"stages",sorted(set(st)),"water",max(float(r['water_stress']) for r in rs),"N",max(float(r['nitrogen_stress']) for r in rs))
