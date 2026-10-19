"""Wheat N stress law in Cycles output (2026-10-19): ratio of above-ground N concentration to the critical concentration at the plant's biomass (engine n_critical_pct, wheat crop dict) against Cycles' nitrogen_stress, 16 fresh sites, N=0/90/150, FALLN=60.
Compared with the corn law the engine uses for every crop: stress = Smax x ((R0 - r)/(R0 - R1))^q for r between R1 and R0."""
import os,sys,json,csv,shutil,subprocess
os.environ["N_LEVELS"]="0,90,150"; os.environ.setdefault("REGIONAL","0"); os.environ["FALLN"]="60"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E, run_validation_rotation2 as r2
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatN"; m.write_inputs(fs,lat,lon,wx,soil,cl); rows=[]
    for N in (0,90,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N)); subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
        for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999': continue
            ab=float(x['aboveground_biomass']); 
            if ab<0.3: continue
            conc=float(x['aboveground_nitrogen_concentration'])/10.0   # g/kg to percent
            nc=E.n_critical_pct(float(x['biomass'])*10,r2.WHEAT,r2.WHEAT.get("n_stress_crit_floor",E.N_STRESS_CRIT_FLOOR_MGHA))
            rows.append((conc/nc,float(x['nitrogen_stress'])/100.0,N))
        shutil.rmtree(d,ignore_errors=True)
    return rows
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:16]
    with Pool(4) as p: R=sum(p.map(one,[(k,S[k]) for k in ks]),[])
    A=np.array(R); np.save('/tmp/w/wheat_nlaw.npy',A); print(len(A),'days')
    law=lambda r:E.N_STRESS_SMAX*np.clip((E.N_STRESS_R0-r)/(E.N_STRESS_R0-E.N_STRESS_R1),0,1)**E.N_STRESS_Q
    print('ratio bin: n | Cycles stress median (mean) | engine corn law at bin centre')
    for lo in np.arange(0.1,1.5,0.1):
        k=(A[:,0]>=lo)&(A[:,0]<lo+0.1)
        if k.sum()>100: print(f' {lo:.1f}-{lo+.1:.1f}: {k.sum():6d} | {np.median(A[k,1]):.3f} ({A[k,1].mean():.3f}) | {law(lo+.05):.3f}')
    k=(A[:,0]>0.1)&(A[:,0]<1.6); print('rms engine corn law vs Cycles wheat %.4f'%np.sqrt(np.mean((law(A[k,0])-A[k,1])**2)))
