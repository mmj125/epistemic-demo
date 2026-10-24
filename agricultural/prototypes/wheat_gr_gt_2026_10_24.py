"""Wheat daily growth against Cycles on unstressed days, by mean temperature (2026-10-24): Cycles' total biomass gain per MJ of solar radiation intercepted the previous day, and the engine's applied growth, its radiation-limited term GR and its transpiration-limited term GT per MJ intercepted.
24 sites, N=90, FALLN=60, days where Cycles' water and N stress are under 2 percent. Usage: python3 wheat_gr_gt_2026_10_24.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); CY=m.CY
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
    fs=site+"wheatgg"; m.write_inputs(fs,lat,lon,wx,soil,cl); N=90
    open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N)); subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
    CR=rd(d+"dailyWinterWheat.csv"); shutil.rmtree(d,ignore_errors=True)
    cyc={x['date']:(float(x['biomass']),float(x['radiation_interception']),float(x['water_stress']),float(x['nitrogen_stress']),x['stage']) for x in CR if x['biomass']!='-999'}
    R=W.engine_chain(wx,soil,cl,N,None); rows=[]
    for y1,res in R.items():
        y=y1-1; d0=datetime.date(y,1,1)+datetime.timedelta(days=287); prevc=None; preve=None; pk=None
        for i,h in enumerate(res.get("history") or []):
            dt=d0+datetime.timedelta(days=i); k=dt.isoformat(); w=wx.get(dt.year,{}).get(dt.timetuple().tm_yday)
            if k in cyc and w and y1>=1983 and pk in cyc:
                c=cyc[k]; cp=cyc[pk]
                rows.append([(w['tx']+w['tn'])/2,w['solar'],cp[1],c[0]-cp[0],c[2],c[3],preve if preve is not None else 0.0,h["gr"],h["gt"],h["dgb"]*100.0,h["water_stress"],h["n_stress"],dt.month])
            preve=h["canopy"]; pk=k
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); np.save('/tmp/w/wheat_grgt.npy',A); print(len(A),"days")
    k=(A[:,4]<2)&(A[:,5]<2)&(A[:,2]>0.03)&(A[:,6]>0.03)
    print(f"unstressed days {k.sum()}; engine water factor mean {A[k,10].mean():.3f}, N factor {A[k,11].mean():.3f}")
    print("tmean | Cycles g/MJ (growth per intercepted MJ) | engine applied | engine GR | engine GT   (g/MJ, own previous-day canopy)")
    for lo in range(0,24,3):
        j=k&(A[:,0]>=lo)&(A[:,0]<lo+3)
        if j.sum()<300: continue
        ic=(A[j,1]*A[j,2]).sum(); ie=(A[j,1]*A[j,6]).sum()
        print(f" {lo:2d}..{lo+3:2d} n={j.sum():6d} | {100*A[j,3].sum()/ic:.2f} | {A[j,9].sum()/ie:.2f} | {A[j,7].sum()/ie:.2f} | {A[j,8].sum()/ie:.2f}")
