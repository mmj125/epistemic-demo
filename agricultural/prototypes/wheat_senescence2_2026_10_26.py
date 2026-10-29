"""What in Cycles' winter wheat season sets late canopy loss? (2026-10-26) Per season (24 held-out sites, N=0 and 90, FALLN=60, Cycles output only): late canopy ratio = mean canopy at TTf 0.85 to 0.95 over the documented unstressed shape (6,-20,-16,16, plateau 0.853) at the same TTf,
regressed on the mean water factor and N factor in TTf 0.3 to 0.7 and in TTf 0.7 to 0.95. TTf = thermal_time / thermal time on the season's last growing day. Usage: FALLN=60 python3 wheat_senescence2_2026_10_26.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
F_=json.load(open('sitesets/fresh94.json')); S24_=json.load(open('/tmp/w/s24.json')); S={k:F_[k] for k in sorted(F_) if k not in S24_}; S={k:S[k] for k in sorted(S)[::3][:24]}; CY=m.CY
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def shape(x,eix=0.853): return eix/(1+np.exp(6-20*x)+np.exp(-16+16*x))
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatsen2"; m.write_inputs(fs,lat,lon,wx,soil,cl); rows=[]
    for N in (0,90):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
        subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"; CR=[x for x in rd(d+"dailyWinterWheat.csv") if x["biomass"]!="-999"]; shutil.rmtree(d,ignore_errors=True)
        by={}
        for x in CR:
            dt=datetime.date.fromisoformat(x["date"]); y=dt.year if dt.month>=10 else dt.year-1; by.setdefault(y,[]).append(x)
        for y,L in by.items():
            if len(L)<150: continue
            tt=np.array([float(x["thermal_time"]) for x in L]); x=tt/tt.max(); ci=np.array([float(x_["radiation_interception"]) for x_ in L]); w=1-np.array([float(x_["water_stress"]) for x_ in L])/100; n=1-np.array([float(x_["nitrogen_stress"]) for x_ in L])/100
            late=(x>=0.85)&(x<=0.95); mid=(x>=0.3)&(x<0.7); lt=(x>=0.7)&(x<=0.95)
            if late.sum()<3 or mid.sum()<10 or lt.sum()<5: continue
            rows.append([ (ci[late]/shape(x[late])).mean(), w[mid].mean(), n[mid].mean(), w[lt].mean(), n[lt].mean(), ci[mid].max() ])
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[]),float); print(len(A),"seasons; late canopy ratio mean %.2f sd %.2f"%(A[:,0].mean(),A[:,0].std()))
    names=["water 0.3-0.7","N 0.3-0.7","water 0.7-0.95","N 0.7-0.95"]
    for i,nm in enumerate(names): print(f" corr(late ratio, {nm}) {np.corrcoef(A[:,0],A[:,1+i])[0,1]:+.2f}")
    X=np.column_stack([np.ones(len(A)),A[:,1:5]]); b,res,_,_=np.linalg.lstsq(X,A[:,0],rcond=None); pred=X@b; print("regression coefs",np.round(b,2),"R2 %.2f"%(1-((A[:,0]-pred)**2).sum()/((A[:,0]-A[:,0].mean())**2).sum()))
    for nm,col in (("water late only",[3]),("N late only",[4]),("water both windows",[1,3]),("N both windows",[2,4])):
        X=np.column_stack([np.ones(len(A))]+[A[:,c] for c in col]); b=np.linalg.lstsq(X,A[:,0],rcond=None)[0]; pr=X@b; print(f" {nm:22s} R2 {1-((A[:,0]-pr)**2).sum()/((A[:,0]-A[:,0].mean())**2).sum():.2f}  coefs {np.round(b,2)}")
