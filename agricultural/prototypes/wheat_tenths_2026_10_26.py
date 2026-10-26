"""Winter wheat in season, engine against Cycles by tenth of the season's thermal time (2026-10-26): canopy, water stress, N stress, above-ground biomass and daily biomass gain, 24 sites, N=90 with FALLN=60. Engine: record_history rows, Cycles: dailyWinterWheat.csv.
Usage: FALLN=60 python3 wheat_tenths_2026_10_26.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
F_=json.load(open('sitesets/fresh94.json')); S24_=json.load(open('/tmp/w/s24.json')); S={k:F_[k] for k in sorted(F_) if k not in S24_}; S={k:S[k] for k in sorted(S)[::3][:24]}; CY=m.CY   # 24 fresh94 sites outside the 24-site tuning set
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatt"; m.write_inputs(fs,lat,lon,wx,soil,cl); N=90
    open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
    subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
    CR=rd(d+"dailyWinterWheat.csv"); shutil.rmtree(d,ignore_errors=True)
    cyc={x["date"]:x for x in CR if x["biomass"]!="-999"}
    R=W.engine_chain(wx,soil,cl,N,None); rows=[]
    for y1,res in R.items():
        y=y1-1; d0=datetime.date(y,1,1)+datetime.timedelta(days=287); H=res.get("history") or []
        prev_e=None; prev_c=None
        for i,h in enumerate(H):
            dt=(d0+datetime.timedelta(days=i)).isoformat()
            if dt in cyc and y1>=1983:
                c=cyc[dt]; ab_c=float(c["biomass"]) ; ab_e=h["ag_mg_ha"]
                rows.append([min(int(h["ttf"]*10),9),h["canopy"],float(c["radiation_interception"]),h["water_stress"],1-float(c["water_stress"])/100,h["n_stress"],1-float(c["nitrogen_stress"])/100,ab_e,ab_c,
                             (ab_e-prev_e) if prev_e is not None else np.nan,(ab_c-prev_c) if prev_c is not None else np.nan])
                prev_e=ab_e; prev_c=ab_c
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[]),float); np.save('/tmp/w/wheat_tenths.npy',A); print(len(A),"days")
    print("tenth | canopy engine Cycles | water factor | N factor | above-ground biomass | daily gain (Mg/ha/day)   [engine then Cycles]")
    for t in range(10):
        k=A[:,0]==t
        if k.sum()>100: print(f" {t} | {A[k,1].mean():.2f} {A[k,2].mean():.2f} | {A[k,3].mean():.2f} {A[k,4].mean():.2f} | {A[k,5].mean():.2f} {A[k,6].mean():.2f} | {np.nanmean(A[k,7]):.2f} {np.nanmean(A[k,8]):.2f} | {np.nanmean(A[k,9]):.3f} {np.nanmean(A[k,10]):.3f}")
