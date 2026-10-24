"""Does the engine's N stress law reproduce Cycles' stress from Cycles' own states? (2026-10-19) Corn, 24 sites, N=0/150/400. From Cycles' daily output: plant N (total_nitrogen), above-ground and total biomass -> the engine's formula
(above-ground N concentration over the critical concentration at total biomass, 1 - Smax x ((R0-r)/(R0-R1))^q) -> compared with Cycles' nitrogen_stress, by N rate and thermal-time fraction. Bias and rms."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150,400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E, run_validation as rv
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"; rows=[]
    for r in rd(d+"dailyCornRM.90.csv"):
        if r['biomass']=='-999': continue
        tb=float(r['biomass']); ab=float(r['aboveground_biomass']); tn=float(r['total_nitrogen']); ttf=float(r['thermal_time'])/1800.0
        if ab<0.2 or tb<0.3: continue
        rows.append((N,ttf,1.0-float(r['nitrogen_stress'])/100.0 if float(r['nitrogen_stress'])>1.5 else 1.0-float(r['nitrogen_stress']),tb,ab,tn))
    shutil.rmtree(d,ignore_errors=True); return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150,400)]),[])); np.save('/tmp/w/nlaw_raw.npy',A); print(len(A),'days')
    def law(tb,ab,tn,floor):
        ag=E.N_AG_FRACTION*tn/(ab*10); crit=np.array([E.n_critical_pct(x,rv.CORN,floor) for x in tb]); r=ag/crit
        return 1.0-E.N_STRESS_SMAX*np.clip((E.N_STRESS_R0-r)/(E.N_STRESS_R0-E.N_STRESS_R1),0,1)**E.N_STRESS_Q
    for fl in (None,0.3,0.6,1.5,2.5):
        eng=law(A[:,3],A[:,4],A[:,5],fl); print('floor',fl)
        for N in (0,150):
            out=[]
            for lo in (0.1,0.25,0.4,0.55,0.7,0.85):
                k=(A[:,0]==N)&(A[:,1]>=lo)&(A[:,1]<lo+0.15)
                out.append(f'{eng[k].mean()-A[k,2].mean():+.3f}')
            print(f'  N={N} bias by ttf bin (0.1,.25,.4,.55,.7,.85): '+' '.join(out)+f'   rms {np.sqrt(np.mean((eng[A[:,0]==N]-A[A[:,0]==N,2])**2)):.3f}')
