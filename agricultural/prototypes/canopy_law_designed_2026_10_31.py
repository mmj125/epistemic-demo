"""Designed Cycles runs (2026-10-31): the canopy law of corn under constant, unstressed weather. Constant weather, 3 mm rain a day, N 400, so water and N stress stay near zero and the canopy is a function of
thermal time alone. Fits Eq. 6 (plateau, a, b, c, d) to interception against thermal_time / MATURITY_TT and shows how the fit moves with temperature, MATURITY_TT, density and planting day. Cycles only."""
import re,subprocess,shutil,csv,os,numpy as np
from scipy.optimize import least_squares
CY="/tmp/cycles-run15"; BASE="f001_450_1020"
def rd(p): return [r for r in csv.DictReader(l for l in open(p) if not l.startswith('#'))]
def run(T=22.0,half=6.0,mat=None,dens=1.0,doy=110,rain=3.0,solar=20.0,wind=2.0,rh=65.0,msc=100,field=None,val=None):
    nm="cld"
    rows=["LATITUDE                42.000000","ALTITUDE                0.000000","SCREENING_HEIGHT        10.0","YEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND","####    ###     mm      deg C   deg C   MJ/m2   %       %       m/s"]
    for y in (1980,1981):
        for d in range(1,367 if y==1980 else 366): rows.append(f"{y}\t{d}\t{rain:.4f}\t{T+half:.2f}\t{T-half:.2f}\t{solar:.4f}\t{rh:.2f}\t{rh:.2f}\t{wind:.3f}")
    open(f"{CY}/input/{nm}.weather","w").write("\n".join(rows)+"\n")
    shutil.copy(f"{CY}/input/{BASE}.soil",f"{CY}/input/{nm}.soil")
    cf="GenericCrops.crop"
    if field:
        t=open(f"{CY}/input/GenericCrops.crop").read(); i=t.index("CornRM.90"); j=t.find("\nNAME",i+10); j=len(t) if j<0 else j
        blk=re.sub(rf"(?m)^{field}\s+\S+",f"{field}                 {val}",t[i:j]); open(f"{CY}/input/{nm}.crop","w").write(t[:i]+blk+t[j:]); cf=f"{nm}.crop"
    c=open(f"{CY}/input/{BASE}N400.ctrl").read().replace(f"{BASE}N400.operation",f"{nm}.operation").replace(f"{BASE}.soil",f"{nm}.soil").replace(f"{BASE}.weather",f"{nm}.weather").replace("GenericCrops.crop",cf).replace("SIMULATION_END_YEAR     2016","SIMULATION_END_YEAR     1981")
    open(f"{CY}/input/{nm}.ctrl","w").write(c)
    op=open(f"{CY}/input/{BASE}N400.operation").read()
    op=re.sub(r"(?m)^DENSITY\s+\S+",f"DENSITY                             {dens}",op); op=re.sub(r"(?m)^MAXIMUM_SOIL_COVERAGE\s+\S+",f"MAXIMUM_SOIL_COVERAGE               {msc}",op)
    op=re.sub(r"(?m)^(PLANTING\s*\nYEAR\s+\S+\s*\n)DOY\s+\S+\s*\nEND_DOY\s+\S+",rf"\1DOY                                 {doy}\nEND_DOY                             {doy+20}",op)
    open(f"{CY}/input/{nm}.operation","w").write(op)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"
    D=rd(d+"dailyCornRM.90.csv"); shutil.rmtree(d,ignore_errors=True)
    for e in ("ctrl","soil","operation","weather","crop"):
        if os.path.exists(f"{CY}/input/{nm}.{e}"): os.remove(f"{CY}/input/{nm}.{e}")
    D=[r for r in D if r['date'].startswith('1981') and r['biomass']!='-999']
    return D
def fit(D,mat=1800.0):
    x=np.array([float(r['thermal_time'])/mat for r in D]); y=np.array([float(r['radiation_interception']) for r in D]); ws=np.array([float(r['water_stress']) for r in D]); ns=np.array([float(r['nitrogen_stress']) for r in D])
    f=lambda p: p[0]/(1+np.exp(p[1]+p[2]*x)+np.exp(p[3]+p[4]*x))-y
    r=least_squares(f,[0.95,6,-20,-15,16]); return r.x,np.sqrt((r.fun**2).mean()),ws.max(),ns.max(),y.max(),len(x)
if __name__=="__main__":
    def show(lbl,mat=1800.0,**kw):
        D=run(**kw); p,rms,w,n,ymax,k=fit(D,mat); print(f"{lbl:28s} n{k:4d} plateau {p[0]:.3f} a {p[1]:6.2f} b {p[2]:7.2f} c {p[3]:7.2f} d {p[4]:6.2f} | -a/b {-p[1]/p[2]:.3f} -c/d {-p[3]/p[4]:.3f} | rms {rms:.4f} max water stress {w:.1f}% N stress {n:.1f}% peak {ymax:.3f}",flush=True)
    show("base T22")
    show("T 18",T=18.0); show("T 26",T=26.0)
    show("maturity 1500",mat=1500.0,field="MATURITY_TT",val=1500); show("maturity 2100",mat=2100.0,field="MATURITY_TT",val=2100)
    show("density 1.2",dens=1.2); show("density 0.8",dens=0.8)
    show("planting DOY 130",doy=130)
