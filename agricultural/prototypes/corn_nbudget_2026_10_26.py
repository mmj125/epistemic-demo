"""Corn N budget by crop year, engine against Cycles (2026-10-26): plant N at harvest (Cycles dailyCornRM.90.csv total_nitrogen, maximum in the year), grain, and the annual loss terms (Cycles annualN.csv), 16 fresh94 sites not in the 24-site set, N=0/150/400.
Usage: python3 corn_nbudget_2026_10_26.py"""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150,400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
F=json.load(open('sitesets/fresh94.json')); S24=json.load(open('/tmp/w/s24.json')); SITES=[k for k in sorted(F) if k not in S24][:16]
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=F[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (0,150,400):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
        CR=rd(d+"dailyCornRM.90.csv"); H=rd(d+"harvest.csv") if os.path.exists(d+"harvest.csv") else []; DN=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
        pn={}; hd={}
        for r in CR:
            if r['total_nitrogen'] not in ('-999',''):
                y=int(r['date'][:4])
                if float(r['total_nitrogen'])>=pn.get(y,0): pn[y]=float(r['total_nitrogen']); hd[y]=r['date']
        nm={}; mn={r['date']:float(r['profile_soil_NO3'])+float(r['profile_soil_NH4']) for r in DN}
        for r in DN:
            y=int(r['date'][:4]); a=nm.setdefault(y,[0,0,0,0]); a[0]+=float(r['mineralization']); a[1]+=float(r['immobilization']); a[2]+=float(r['net_mineralization']); a[3]+=float(r['nitrification'])
        E=m.engine(site,wx,soil,cl,N,'leadin')
        for y,e in E.items():
            if y in pn and y>=1983: out.append([N,pn[y],e.get('n_plant_kg_ha') or 0,e.get('n_uptake_kg_ha') or 0,nm[y][2],nm[y][3],mn.get(hd[y],np.nan),e.get('n_remaining_kg_ha') or 0])
    return out
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,SITES),[])); np.save('/tmp/w/corn_nbudget.npy',A)
    for N in (0,150,400):
        k=A[:,0]==N; print(f"N={N} n={k.sum()}  plant N at harvest Cycles {A[k,1].mean():.1f} engine plant {A[k,2].mean():.1f} engine uptake {A[k,3].mean():.1f}  | Cycles net min {A[k,4].mean():.1f} nitrification {A[k,5].mean():.1f} | mineral N left at harvest Cycles {np.nanmean(A[k,6]):.1f} engine {A[k,7].mean():.1f}")
