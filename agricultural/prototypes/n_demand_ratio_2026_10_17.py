"""Ratio of Cycles' unstressed marginal total-N concentration of new growth (dTotalN/dTotalBiomass, days with N multiplier >= 0.97) to the engine's critical-curve marginal a*(1-b)*W^-b, by total-biomass class, for corn, silage corn and winter wheat. One measured value per crop for the N demand scale. Usage: CROPS=corn,silage,wheat python3 n_demand_ratio_2026_10_17.py"""
import os,sys,json,csv,shutil,subprocess,glob
os.environ["N_LEVELS"]="0,150,400"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np
import run_validation_multisite as m
import run_validation_multisite_wheat as W
from multiprocessing import Pool
CY=m.CY
PARAM={'corn':(0.055,0.4,'CornRM.90'),'silage':(0.055,0.4,'CornSilageRM.90'),'wheat':(0.07,0.45,'WinterWheat')}
def rows(d,crop):
    f=[x for x in glob.glob(d+"daily*.csv") if not any(k in os.path.basename(x) for k in ("Water","Environ","Residue","SoilC","SoilLayers","dailyN.csv"))][0]
    out=[];prev=None
    for x in csv.DictReader(open(f)):
        if x['date'][0]=='#' or x['biomass']=='-999': prev=None; continue
        r=(float(x['biomass']),float(x['total_nitrogen']),1-float(x['nitrogen_stress'])/100)
        if prev is not None: out.append((r[0],r[2],r[0]-prev[0],r[1]-prev[1]))
        prev=r
    return out
def one(a):
    crop,site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+crop; m.write_inputs(fs,lat,lon,wx,soil,cl); out=[]
    for N in ((0,90,150) if crop=='wheat' else (0,150,400)):
        if crop=='wheat': open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+(W.FERT%(N/0.32) if N>0 else ""))
        elif crop=='silage':
            p=f"{CY}/input/{fs}N{N}.operation"; t=open(p).read(); open(p,"w").write(t.replace("CornRM.90","CornSilageRM.90"))
        subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
        try: out+=rows(d,crop)
        except Exception as e: print("ERR",fs,N,repr(e),flush=True)
        shutil.rmtree(d,ignore_errors=True)
    return crop,out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json")); jobs=[(c,k,v) for c in os.environ.get("CROPS","corn,silage,wheat").split(",") for k,v in list(S.items())[:16]]
    with Pool(4) as p: R=p.map(one,jobs)
    for c in os.environ.get("CROPS","corn,silage,wheat").split(","):
        A=np.array(sum([o for cc,o in R if cc==c],[])); a,b,_=PARAM[c]
        print(c,"days",len(A))
        tot=[]
        for lo,hi in ((0.1,1),(1,4),(4,10),(10,40)):
            k=(A[:,0]>=lo)&(A[:,0]<hi)&(A[:,1]>=.97)&(A[:,2]>0)
            if k.sum()<50: continue
            Wm=A[k,0].mean(); cy=A[k,3].sum()/(A[k,2].sum()*10); en=a*100*(1-b)*Wm**(-b) if Wm>=1 else a*100
            print(f"   W {lo}-{hi}: Cycles {cy:.2f}%  engine curve {en:.2f}%  ratio {cy/en:.2f} (n {k.sum()})")
            tot.append((cy/en,A[k,2].sum()))
        print("   growth-weighted ratio", round(sum(r*w for r,w in tot)/sum(w for r,w in tot),2))
