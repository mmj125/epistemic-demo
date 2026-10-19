"""Aboveground share of plant N in Cycles by growth stage, and the engine N stress law with the exact aboveground concentration (2026-10-19). Corn, 24 sites, N=0/150/400."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150,400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"; rows=[]
    for r in rd(d+"dailyCornRM.90.csv"):
        if r['biomass']=='-999': continue
        tb=float(r['biomass']); ab=float(r['aboveground_biomass']); tn=float(r['total_nitrogen']); an=float(r['aboveground_nitrogen']); conc=float(r['aboveground_nitrogen_concentration'])/10.0; ttf=float(r['thermal_time'])/1800.0
        if ab<0.2 or tn<=0: continue
        cf=1.0-float(r['nitrogen_stress'])/100.0 if float(r['nitrogen_stress'])>1.5 else 1.0-float(r['nitrogen_stress'])
        rows.append((N,ttf,cf,tb,ab,tn,an,conc))
    shutil.rmtree(d,ignore_errors=True); return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150,400)]),[])); np.save('/tmp/w/agn.npy',A); N,ttf,cf,tb,ab,tn,an,conc=A.T
    print('aboveground N share of plant N, by ttf: '+' '.join(f'{lo:.2f}:{(an/tn)[(ttf>=lo)&(ttf<lo+.15)].mean():.3f}' for lo in (0.1,0.25,0.4,0.55,0.7,0.85)))
    chk=np.abs(conc-an/(ab*10)); print('conc column vs an/(ab*10): max diff %.4f'%chk.max())
    crit=np.array([E.n_critical_pct(x,rv.CORN,None) for x in tb]); law=lambda r:1.0-E.N_STRESS_SMAX*np.clip((E.N_STRESS_R0-r)/(E.N_STRESS_R0-E.N_STRESS_R1),0,1)**E.N_STRESS_Q
    for lab,ratio in (('engine: 0.88 x plant N',(E.N_AG_FRACTION*tn/(ab*10))/crit),('exact aboveground concentration',conc/crit)):
        e=law(ratio); print(lab+': bias by ttf bin (.1,.25,.4,.55,.7,.85)')
        for n in (0,150,400):
            print(f'  N={n}: '+' '.join(f'{e[(N==n)&(ttf>=lo)&(ttf<lo+.15)].mean()-cf[(N==n)&(ttf>=lo)&(ttf<lo+.15)].mean():+.3f}' for lo in (0.1,0.25,0.4,0.55,0.7,0.85)),f' rms {np.sqrt(np.mean((e[N==n]-cf[N==n])**2)):.3f}')
