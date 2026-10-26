"""Does stress speed up Cycles' winter wheat senescence? (2026-10-26) Per season: mean combined stress factor (water x N, from planting to TTf 0.7) against canopy at TTf 0.8 to 1.0 relative to the season's plateau canopy, Cycles and engine, 24 fresh94 sites outside the tuning set, N=0 and 90 (FALLN=60). Usage: FALLN=60 python3 wheat_senescence_2026_10_26.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
F_=json.load(open('sitesets/fresh94.json')); S24_=json.load(open('/tmp/w/s24.json')); S={k:F_[k] for k in sorted(F_) if k not in S24_}; S={k:S[k] for k in sorted(S)[::3][:24]}; CY=m.CY
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatsen"; m.write_inputs(fs,lat,lon,wx,soil,cl); rows=[]
    for N in (0,90):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
        subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"; CR=[x for x in rd(d+"dailyWinterWheat.csv") if x["biomass"]!="-999"]; shutil.rmtree(d,ignore_errors=True)
        by={}
        for x in CR:
            dt=datetime.date.fromisoformat(x["date"]); y=dt.year if dt.month>=10 else dt.year-1; by.setdefault(y,{})[x["date"]]=x
        R=W.engine_chain(wx,soil,cl,N,None)
        for y1,res in R.items():
            y=y1-1
            if y not in by or y1<1983: continue
            d0=datetime.date(y,1,1)+datetime.timedelta(days=287); H=res.get("history") or []
            cyc=by[y]; e=[];c=[]
            for i,h in enumerate(H):
                dt=(d0+datetime.timedelta(days=i)).isoformat()
                if dt in cyc: x=cyc[dt]; e.append((h["ttf"],h["canopy"],h["water_stress"]*h["n_stress"])); c.append((h["ttf"],float(x["radiation_interception"]),(1-float(x["water_stress"])/100)*(1-float(x["nitrogen_stress"])/100)))
            if len(e)<100: continue
            def stat(v):
                v=np.array(v); sel=(v[:,0]>0.5)&(v[:,0]<0.7)
                if sel.sum()==0 or ((v[:,0]>=0.8)&(v[:,0]<1.0)).sum()==0: return (np.nan,np.nan)
                pl=v[sel,1].max(); st=v[v[:,0]<0.7,2].mean(); late=v[(v[:,0]>=0.8)&(v[:,0]<1.0),1].mean()
                return st,late/max(pl,1e-6)
            rows.append([N]+list(stat(c))+list(stat(e)))
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[]),float); A=A[~np.isnan(A).any(axis=1)]; print(len(A),"seasons")
    print("stress tercile (Cycles, planting to TTf 0.7) | n | stress Cycles engine | late canopy / plateau, Cycles engine")
    q=np.quantile(A[:,1],[1/3,2/3])
    for nm,k in (("most stressed",A[:,1]<q[0]),("middle",(A[:,1]>=q[0])&(A[:,1]<q[1])),("least stressed",A[:,1]>=q[1])):
        print(f" {nm:15s} | {k.sum():4d} | {A[k,1].mean():.2f} {A[k,3].mean():.2f} | {A[k,2].mean():.2f} {A[k,4].mean():.2f}")
    print("corr(late canopy ratio, stress): Cycles %.2f engine %.2f"%(np.corrcoef(A[:,1],A[:,2])[0,1],np.corrcoef(A[:,3],A[:,4])[0,1]))
