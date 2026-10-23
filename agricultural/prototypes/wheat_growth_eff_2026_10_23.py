"""Wheat winter growth efficiency (2026-10-23): above-ground biomass gain per MJ of intercepted solar radiation, by calendar month and by mean temperature, engine against Cycles, N=90, 24 sites, FALLN=60 (days with both models in season)."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); CY=m.CY
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatge"; m.write_inputs(fs,lat,lon,wx,soil,cl); N=90
    open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N)); subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
    CR=rd(d+"dailyWinterWheat.csv"); shutil.rmtree(d,ignore_errors=True)
    cyc={x['date']:(float(x['aboveground_biomass']),float(x['radiation_interception']),float(x['water_stress']),float(x['nitrogen_stress'])) for x in CR if x['biomass']!='-999'}
    R=W.engine_chain(wx,soil,cl,N,None); rows=[]
    for y1,res in R.items():
        y=y1-1; d0=datetime.date(y,1,1)+datetime.timedelta(days=287); prev_e=None; prev_c=None
        for i,h in enumerate(res.get("history") or []):
            dt=d0+datetime.timedelta(days=i); k=dt.isoformat(); w=wx.get(dt.year,{}).get(dt.timetuple().tm_yday)
            if k in cyc and w and y1>=1983:
                e_ag=h["ag_mg_ha"]; c_ag=cyc[k][0]
                if prev_e is not None and prev_c is not None:
                    rows.append([dt.month,(w['tx']+w['tn'])/2,w['solar'],h["canopy"],cyc[k][1],e_ag-prev_e,c_ag-prev_c,h["water_stress"],1-cyc[k][2]/100,h["n_stress"],1-cyc[k][3]/100])
                prev_e,prev_c=e_ag,c_ag
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); np.save('/tmp/w/wheat_ge.npy',A); print(len(A),"days")
    print("month | growth Mg/ha/day engine Cycles | intercepted radiation MJ/m2/day engine Cycles | efficiency g/MJ engine Cycles | water factor engine Cycles | N factor engine Cycles")
    for mo in list(range(10,13))+list(range(1,8)):
        k=A[:,0]==mo
        if k.sum()<200: continue
        ie=(A[k,2]*A[k,3]).sum(); ic=(A[k,2]*A[k,4]).sum()
        print(f" {mo:2d} | {A[k,5].mean():+.4f} {A[k,6].mean():+.4f} | {(A[k,2]*A[k,3]).mean():.2f} {(A[k,2]*A[k,4]).mean():.2f} | {100*A[k,5].sum()/ie:.2f} {100*A[k,6].sum()/ic:.2f} | {A[k,7].mean():.2f} {A[k,8].mean():.2f} | {A[k,9].mean():.2f} {A[k,10].mean():.2f}")
    print("by mean temperature (winter months Nov to Mar): efficiency g/MJ engine, Cycles")
    w=np.isin(A[:,0],[11,12,1,2,3])
    for lo in range(-10,12,4):
        k=w&(A[:,1]>=lo)&(A[:,1]<lo+4)
        if k.sum()>300: print(f" {lo:3d}..{lo+4:3d} n={k.sum():6d}: {100*A[k,5].sum()/(A[k,2]*A[k,3]).sum():.2f} {100*A[k,6].sum()/(A[k,2]*A[k,4]).sum():.2f}")
