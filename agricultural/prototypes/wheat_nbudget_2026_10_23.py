"""Wheat N pools and fluxes by calendar month, engine against Cycles (2026-10-23), N=90 with FALLN=60, 24 sites (the in-season history only: planting to harvest). Cycles dailyN.csv: profile nitrate and ammonium,
net mineralization, nitrification, denitrification, leaching, volatilization. Engine history: n_no3, n_nh4, netmin, nitr, denit, leach. Usage: FALLN=60 python3 wheat_nbudget_2026_10_23.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); CY=m.CY
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatnb"; m.write_inputs(fs,lat,lon,wx,soil,cl); N=90
    open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
    subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
    D=rd(d+"dailyN.csv"); CR=rd(d+"dailyWinterWheat.csv") if os.path.exists(d+"dailyWinterWheat.csv") else []; shutil.rmtree(d,ignore_errors=True); pn={x["date"]:float(x["total_nitrogen"]) for x in CR if x["biomass"]!="-999"}; ab={x["date"]:(float(x["aboveground_biomass"]),float(x["radiation_interception"]),float(x["temperature_factor"])) for x in CR if x["biomass"]!="-999"}
    cyc={x['date']:(float(x['profile_soil_NO3']),float(x['profile_soil_NH4']),float(x['net_mineralization']),float(x['nitrification']),float(x['denitrification']),float(x['NO3_leaching'])+float(x['NH4_leaching']),float(x['volatilization'])) for x in D}
    R=W.engine_chain(wx,soil,cl,N,None); rows=[]
    for y1,res in R.items():
        y=y1-1; d0=datetime.date(y,1,1)+datetime.timedelta(days=287)
        for i,h in enumerate(res.get("history") or []):
            dt=(d0+datetime.timedelta(days=i)).isoformat()
            if dt in cyc and y1>=1983:
                c=cyc[dt]; rows.append([int(dt[5:7]),h["n_no3"] or 0,c[0],h["n_nh4"] or 0,c[1],h["netmin"],c[2],h["nitr"],c[3],h["denit"],c[4],h["leach"],c[5],pn.get(dt,np.nan),h["n_plant"] or 0,ab.get(dt,(np.nan,)*3)[0],h["ag_mg_ha"]/10.0,ab.get(dt,(np.nan,)*3)[1],h["canopy"]])
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); np.save('/tmp/w/wheat_nbudget.npy',A); print(len(A),"days")
    print("month | nitrate kg/ha engine Cycles | ammonium | net min /day | nitrification /day | denitrification /day | leaching /day | plant N kg/ha | above-ground Mg/ha | canopy   (engine then Cycles)")
    for mo in list(range(10,13))+list(range(1,8)):
        k=A[:,0]==mo
        if k.sum()>200: print(f" {mo:2d} | {A[k,1].mean():5.1f} {A[k,2].mean():5.1f} | {A[k,3].mean():5.1f} {A[k,4].mean():5.1f} | {A[k,5].mean():+.2f} {A[k,6].mean():+.2f} | {A[k,7].mean():.2f} {A[k,8].mean():.2f} | {A[k,9].mean():.3f} {A[k,10].mean():.3f} | {A[k,11].mean():.3f} {A[k,12].mean():.3f} | {A[k,14].mean():5.1f} {np.nanmean(A[k,13]):5.1f} | {A[k,16].mean():.2f} {np.nanmean(A[k,15]):.2f} | {A[k,18].mean():.2f} {np.nanmean(A[k,17]):.2f}")
