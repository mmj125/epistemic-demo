"""Cycles' nitrogen split at harvest (2026-10-19): corn, 24 sites, N=0/150/400, continuous chain. Grain N, residue N, root N against above-ground N concentration, to read the nitrogen harvest index."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    H=rd(d+"harvest.csv"); shutil.rmtree(d,ignore_errors=True); f=float
    return [(N,f(h['total_biomass']),f(h['root_biomass']),f(h['grain_yield']),f(h['aboveground_residue']),f(h['total_nitrogen']),f(h['root_nitrogen']),f(h['grain_nitrogen']),f(h['nitrogen_in_residue'])) for h in H if h['date'][:4]>='1982' and f(h['grain_yield'])>0.5]
if __name__=="__main__":
    jobs=[(s,N) for s in sorted(S) for N in (0,150,400)]
    A=np.array([r for L in Pool(4).map(one,jobs) for r in L]); np.save('/tmp/w/nhi.npy',A); print(len(A),'site-years')
    N,TB,RB,GY,AR,TN,RN,GN,ResN=A.T
    agN=GN+ResN; print('ag N / total N %.3f (sd %.3f); root N / total N %.3f'%((agN/TN).mean(),(agN/TN).std(),(RN/TN).mean()))
    ab=TB-RB; conc=agN/(ab*10)   # percent: kg N / (Mg*1000 kg) *100
    nhi=GN/agN; print('NHI mean %.3f sd %.3f'%(nhi.mean(),nhi.std()))
    for lo,hi in ((0,0.6),(0.6,0.8),(0.8,1.0),(1.0,1.3),(1.3,5)):
        s=(conc>=lo)&(conc<hi)
        if s.sum()>20: print(f' ag N conc {lo}-{hi}%: n {s.sum()} NHI {nhi[s].mean():.3f}  grain conc {(GN[s]/(GY[s]*10)).mean():.2f}%  straw conc {(ResN[s]/(AR[s]*10)).mean():.2f}%')
    X=np.c_[np.ones(len(conc)),conc]; b=np.linalg.lstsq(X,nhi,rcond=None)[0]; print('NHI = %.3f + %.3f x conc, rms %.3f'%(b[0],b[1],np.sqrt(np.mean((X@b-nhi)**2))))
    print('residual C:N (0.4 C) mean of ratios %.1f, ratio of means %.1f'%((0.4*AR*1000/np.maximum(ResN,1e-3)).mean(),0.4*AR.mean()*1000/ResN.mean()))
    print('root C:N (0.4) %.1f'%((0.4*RB*1000/RN).mean()))
