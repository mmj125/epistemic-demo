"""Teacher-forced look at what limits Cycles' daily corn N uptake (2026-10-17). Uptake U = day-to-day change in Cycles' total plant N. On N-stressed days (stress multiplier < 0.9, so uptake is below demand)
U is regressed (log-log) on Cycles' own soil N pool, root-zone nitrate/ammonium concentration, soil moisture, thermal time fraction (a proxy for root depth), and temperature, to see which of them sets the limit.
12 sites, N=0 and N=150. Usage: python3 corn_uptake_limit_2026_10_17.py"""
import os,sys,json,csv,datetime,shutil,subprocess,numpy as np
os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'.')
import run_validation_multisite as m
S=json.load(open("/tmp/w/s24.json")); ks=sorted(S)[:12]; CY=m.CY; rows=[]
for site in ks:
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon; m.write_inputs(site,lat,lon,wx,soil,cl)
    for N in (0,150):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"
        Nn={}; 
        for x in csv.DictReader(open(d+"dailyN.csv")):
            if x["date"][0]!="#": Nn[x["date"]]=float(x["profile_soil_NO3"])+float(x["profile_soil_NH4"])
        L={}
        for x in csv.DictReader(open(d+"dailySoilLayersCN.csv")):
            if x["date"][0]=="#": continue
            no3=[float(x[k]) for k in x if k.startswith("NO3.")]; nh4=[float(x[k]) for k in x if k.startswith("NH4.")]
            L[x["date"]]=(no3,nh4)
        W={}
        for x in csv.DictReader(open(d+"dailyWater.csv")):
            if x["date"][0]!="#": W[x["date"]]=[float(x[k]) for k in x if k.startswith("soil_moisture_content")]
        prev=None
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x["date"][0]=="#" or x["biomass"]=="-999": prev=None; continue
            v=(float(x["total_nitrogen"]),float(x["thermal_time"])/1800,1-float(x["nitrogen_stress"])/100,float(x["biomass"]))
            dt=x["date"]
            if prev is not None and dt in Nn and dt in L and dt in W and v[3]>0.3:
                no3,nh4=L[dt]; n=len(no3)
                rows.append((N,v[0]-prev[0],Nn[dt],np.mean(no3[:2])+np.mean(nh4[:2]),np.mean(no3)+np.mean(nh4),W[dt][0],np.mean(W[dt][:2]),v[1],v[2],v[0],v[3],(wx[int(dt[:4])][datetime.date.fromisoformat(dt).timetuple().tm_yday]["tx"]+wx[int(dt[:4])][datetime.date.fromisoformat(dt).timetuple().tm_yday]["tn"])/2 if int(dt[:4]) in wx else 15))
            prev=v
        shutil.rmtree(d,ignore_errors=True)
A=np.array(rows); np.save("/tmp/w/corn_uptake_limit.npy",A); print("days",len(A))
N,U,P,c12,cAll,th1,th12,ttf,ns,PN,B,tm=A.T
for lbl,mask in (("stressed (ns<0.9)",(ns<0.9)&(U>0.02)),("moderately (0.9-0.99)",(ns>=0.9)&(ns<0.99)&(U>0.02)),("unstressed",(ns>=0.99)&(U>0.02))):
    print(lbl,"n=",mask.sum())
    y=np.log(U[mask])
    cands={"log pool(total)":np.log(P[mask]),"log conc layers1-2":np.log(np.maximum(c12[mask],1e-3)),"log conc all layers":np.log(np.maximum(cAll[mask],1e-3)),"log plantN":np.log(np.maximum(PN[mask],0.1)),"log biomass":np.log(B[mask]),"ttf":ttf[mask],"theta layer1":th1[mask],"theta layers1-2":th12[mask],"air temp":tm[mask]}
    for k,x in cands.items(): print(f"    corr(log U, {k}) = {np.corrcoef(x,y)[0,1]:+.2f}")
    X=np.c_[np.ones(mask.sum()),np.log(np.maximum(c12[mask],1e-3)),np.log(B[mask]),th12[mask]]; co=np.linalg.lstsq(X,y,rcond=None)[0]; r=y-X@co
    print(f"    log U = {co[0]:.2f} + {co[1]:.2f} log(conc 1-2) + {co[2]:.2f} log(biomass) + {co[3]:.2f} theta12   R2 {1-r.var()/y.var():.2f}")
print("U/pool on stressed days: median %.3f, IQR %.3f-%.3f"%tuple(np.percentile((U/P)[(ns<0.9)&(U>0.02)],[50,25,75])))
