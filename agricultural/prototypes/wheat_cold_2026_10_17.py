"""Does Cycles' wheat canopy fall on cold nights? (2026-10-17) Day-over-day change in Cycles radiation_interception (Nov-Apr) against that day's minimum temperature, 16 fresh sites, N=150,
binned by tn. Also the share of winter days with a drop > 0.01 and the mean change by tn bin, plus the crop-file cold damage fields."""
import os,sys,json,csv,datetime,shutil,subprocess,numpy as np
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"; m.write_inputs(fs,lat,lon,wx,soil,cl); N=150
    open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+(W.FERT%(N/0.32)))
    subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"; rows=[]; prev=None
    for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
        if x["date"][0]=="#" or x["biomass"]=="-999": prev=None; continue
        dt=datetime.date.fromisoformat(x["date"]); c=float(x["radiation_interception"])
        if prev is not None and dt.month in (11,12,1,2,3,4):
            w=wx[dt.year][dt.timetuple().tm_yday]; rows.append((w["tn"],c-prev,c,x["stage"]))
        prev=c
    shutil.rmtree(d,ignore_errors=True); return rows
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:16]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    A=np.array([(r[0],r[1],r[2]) for rr in R for r in rr]); k=A[:,2]>0.1
    print("days",k.sum(),"(canopy>0.1)")
    for lo,hi in ((-40,-20),(-20,-15),(-15,-10),(-10,-5),(-5,0),(0,5),(5,40)):
        b=k&(A[:,0]>=lo)&(A[:,0]<hi)
        if b.sum()>20: print(f"tn {lo:4d}..{hi:3d} n={b.sum():6d} mean daily change {A[b,1].mean():+.4f}  share dropping >0.01: {(A[b,1]<-0.01).mean():.3f}  >0.03: {(A[b,1]<-0.03).mean():.3f}")
