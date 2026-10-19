"""Wheat shoot share of new growth versus thermal-time fraction in Cycles output (2026-10-19): 16 fresh sites, N=0 and 150, FALLN=60. Fits the SI Eq. 8 form fsti + (fstf-fsti)/(1+(ttf50/ttf)^e) (crop file fsti .45, fstf .95).
Also reports the engine wheat value (ttf50 0.32) and the corn value (0.42) rms for comparison."""
import os,sys,json,csv,shutil,subprocess
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); os.environ["FALLN"]="60"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatP"; m.write_inputs(fs,lat,lon,wx,soil,cl); out=[]
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N)); subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"; prev=None
        for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999': prev=None; continue
            r=(float(x['thermal_time']),float(x['biomass']),float(x['aboveground_biomass']))
            if prev and r[0]>=prev[0]:
                dt=r[1]-prev[1]; da=r[2]-prev[2]
                if dt>0.03: out.append((r[0]/1800.0,da/dt))
            prev=r
        shutil.rmtree(d,ignore_errors=True)
    return out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:16]
    with Pool(4) as p: R=sum(p.map(one,[(k,S[k]) for k in ks]),[])
    A=np.array(R); np.save('/tmp/w/wheat_part.npy',A); print(len(A),'days; ttf range %.2f-%.2f'%(A[:,0].min(),A[:,0].max()))
    f=lambda t,e,t50:0.45+0.5/(1+(t50/np.maximum(t,1e-6))**e)
    for lo in np.arange(0.0,1.2,0.1):
        k=(A[:,0]>=lo)&(A[:,0]<lo+0.1)
        if k.sum()>30: print(f" ttf {lo:.1f}-{lo+.1:.1f}: n {k.sum():5d} Cycles median {np.median(A[k,1]):.3f} mean {A[k,1].mean():.3f} | form ttf50 .32 {f(lo+.05,4,.32):.3f}  .42 {f(lo+.05,4,.42):.3f}")
    from scipy.optimize import least_squares
    k=(A[:,0]>0.03)&(A[:,0]<1.1)&(A[:,1]>-0.2)&(A[:,1]<1.2)
    for e0 in (2,4,6):
        r=least_squares(lambda p:f(A[k,0],p[0],p[1])-A[k,1],[e0,0.4],loss='soft_l1'); print('free fit exponent %.2f ttf50 %.3f rms %.4f'%(r.x[0],r.x[1],np.sqrt(np.mean((f(A[k,0],*r.x)-A[k,1])**2))))
    r=least_squares(lambda p:f(A[k,0],4,p[0])-A[k,1],[0.4],loss='soft_l1'); print('exponent 4 fixed: ttf50 %.3f rms %.4f'%(r.x[0],np.sqrt(np.mean((f(A[k,0],4,r.x[0])-A[k,1])**2))))
    for t50 in (0.32,0.42): print('ttf50',t50,'rms %.4f'%np.sqrt(np.mean((f(A[k,0],4,t50)-A[k,1])**2)))
