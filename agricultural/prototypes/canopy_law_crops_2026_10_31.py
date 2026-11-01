"""Designed Cycles runs (2026-10-31), other crops: does the unstressed canopy follow Eq. 6 with 6, -20, -16, 15 on TTf = thermal time / (MATURITY_TT - emergence), evaluated half a day back? Constant weather,
5 mm rain a day, N 400. Reports the plateau and rms of that exact law (plateau the only free parameter) and the same with the printed c = -15, d = 16. Cycles only."""
import re,subprocess,shutil,csv,os,numpy as np
from scipy.optimize import least_squares
CY="/tmp/cycles-run15"; BASE="f001_450_1020"
def rd(p): return [r for r in csv.DictReader(l for l in open(p) if not l.startswith('#'))]
def run(suf,crop,T=22.0,rain=5.0,doy=None):
    nm="cldc"
    rows=["LATITUDE                42.000000","ALTITUDE                0.000000","SCREENING_HEIGHT        10.0","YEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND","####    ###     mm      deg C   deg C   MJ/m2   %       %       m/s"]
    for y in (1980,1981):
        for d in range(1,367 if y==1980 else 366): rows.append(f"{y}\t{d}\t{rain:.4f}\t{T+6:.2f}\t{T-6:.2f}\t20.0000\t65.00\t65.00\t2.000")
    open(f"{CY}/input/{nm}.weather","w").write("\n".join(rows)+"\n")
    shutil.copy(f"{CY}/input/{BASE}.soil",f"{CY}/input/{nm}.soil")
    c=open(f"{CY}/input/{BASE}{suf}N400.ctrl").read().replace(f"{BASE}{suf}N400.operation",f"{nm}.operation").replace(f"{BASE}.soil",f"{nm}.soil").replace(f"{BASE}.weather",f"{nm}.weather").replace("SIMULATION_END_YEAR     2016","SIMULATION_END_YEAR     1981")
    c=re.sub(rf"{BASE}{suf}\.(soil|weather)",lambda m: f"{nm}.{m.group(1)}",c)
    open(f"{CY}/input/{nm}.ctrl","w").write(c)
    op=open(f"{CY}/input/{BASE}{suf}N400.operation").read()
    if doy: op=re.sub(r"(?m)^(PLANTING\s*\nYEAR\s+\S+\s*\n)DOY\s+\S+\s*\nEND_DOY\s+\S+",rf"\1DOY                                 {doy}\nEND_DOY                             {doy+20}",op)
    open(f"{CY}/input/{nm}.operation","w").write(op)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"
    D=rd(d+f"daily{crop}.csv"); shutil.rmtree(d,ignore_errors=True)
    for e in ("ctrl","soil","operation","weather"): os.remove(f"{CY}/input/{nm}.{e}")
    return [r for r in D if r['date'].startswith('1981') and r['biomass']!='-999']
def score(D,MAT,TTe,cc,d):
    TT=np.array([float(r['thermal_time']) for r in D]); y=np.array([float(r['radiation_interception']) for r in D]); m=(TT<=MAT)&(np.array([r['crop']!='FALLOW' for r in D]))
    TT=TT[m]; y=y[m]; dday=np.median(np.diff(TT[TT>0.3*MAT]))
    f=lambda p: p[0]/(1+np.exp(6-20*(TT-0.45*dday)/(MAT-TTe))+np.exp(cc+d*(TT-0.45*dday)/(MAT-TTe)))-y
    q=least_squares(f,[0.95]); return q.x[0],np.sqrt((q.fun**2).mean()),abs(q.fun).max()
if __name__=="__main__":
    for suf,crop,MAT,TTe in (("","CornRM.90",1800,65),("sil","CornSilageRM.90",1800,65),("sor","SorghumMS",2050,65),("soy","SoybeanMG.5",2250,70)):
        D=run(suf,crop)
        for lbl,cc,d in (("(-16,15)",-16,15),("printed (-15,16)",-15,16)):
            P,r,mx=score(D,MAT,TTe,cc,d); print(f"{crop:16s} {lbl:17s} plateau {P:.3f} rms {r:.4f} max {mx:.3f}  days {len(D)}",flush=True)
