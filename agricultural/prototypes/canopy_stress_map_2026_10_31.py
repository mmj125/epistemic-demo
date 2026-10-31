"""Noise-free stress to canopy-rate map from designed Cycles runs (2026-10-31). Constant weather, 5 mm rain a day, corn; fertilizer N varied (UAN mass 0 to 1250 kg/ha = 0 to 400 kg N/ha), so the N stress develops
under constant conditions. h = realised canopy increment / increment of the unstressed law (Eq. 6, 6 -20 -16 15, axis TT/(MAT-65), plateau 0.953, mid-day), against the reported nitrogen_stress of the previous row.
Cycles only."""
import re,subprocess,shutil,csv,os,numpy as np
CY="/tmp/cycles-run15"; BASE="f001_450_1020"
def rd(p): return [r for r in csv.DictReader(l for l in open(p) if not l.startswith('#'))]
def run(Nkg,T=22.0,rain=5.0,solar=20.0):
    nm="csm"
    rows=["LATITUDE                42.000000","ALTITUDE                0.000000","SCREENING_HEIGHT        10.0","YEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND","####    ###     mm      deg C   deg C   MJ/m2   %       %       m/s"]
    for y in (1980,1981):
        for d in range(1,367 if y==1980 else 366): rows.append(f"{y}\t{d}\t{rain:.4f}\t{T+6:.2f}\t{T-6:.2f}\t{solar:.4f}\t65.00\t65.00\t2.000")
    open(f"{CY}/input/{nm}.weather","w").write("\n".join(rows)+"\n")
    shutil.copy(f"{CY}/input/{BASE}.soil",f"{CY}/input/{nm}.soil")
    c=open(f"{CY}/input/{BASE}N400.ctrl").read().replace(f"{BASE}N400.operation",f"{nm}.operation").replace(f"{BASE}.soil",f"{nm}.soil").replace(f"{BASE}.weather",f"{nm}.weather").replace("SIMULATION_END_YEAR     2016","SIMULATION_END_YEAR     1981")
    open(f"{CY}/input/{nm}.ctrl","w").write(c)
    op=open(f"{CY}/input/{BASE}N400.operation").read(); mass=Nkg/0.32
    op=re.sub(r"(?m)^MASS\s+\S+",f"MASS                                {mass:.2f}",op)
    open(f"{CY}/input/{nm}.operation","w").write(op)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"
    D=rd(d+"dailyCornRM.90.csv"); shutil.rmtree(d,ignore_errors=True)
    for e in ("ctrl","soil","operation","weather"): os.remove(f"{CY}/input/{nm}.{e}")
    return [r for r in D if r['date'].startswith('1981') and r['biomass']!='-999' and r['crop']!='FALLOW']
P,A,B,C,Dd,MAT,TTe=0.953,6.0,-20.0,-16.0,15.0,1800.0,65.0
def fp(x):
    u=np.exp(A+B*x); v=np.exp(C+Dd*x); return -P*(B*u+Dd*v)/(1+u+v)**2
def hmap(D):
    TT=np.array([float(r['thermal_time']) for r in D]); e=np.array([float(r['radiation_interception']) for r in D]); sN=np.array([float(r['nitrogen_stress']) for r in D])/100; sW=np.array([float(r['water_stress']) for r in D])/100
    out=[]
    for i in range(2,len(TT)):
        if TT[i]>MAT: break
        dx=(TT[i]-TT[i-1])/(MAT-TTe); xm=(0.5*(TT[i]+TT[i-1]))/(MAT-TTe); d=fp(xm)
        if dx>0 and d*dx>0.004 and xm<0.55: out.append((sN[i-1],sN[i],sW[i-1],(e[i]-e[i-1])/(d*dx)))
    return np.array(out)
if __name__=="__main__":
    allr=[]
    for N in (0,25,50,75,100,150,250):
        D=run(N); H=hmap(D); allr.append(H); print(f"N {N:4d}: rise days {len(H):3d} max N stress {H[:,1].max():.2f} max W stress {H[:,2].max():.2f}",flush=True)
    A_=np.vstack(allr); np.save("/tmp/w/csm.npy",A_)
