"""Cycles' own C:N ratios (v1.5.20 dailySoilLayersCN), corn N=0 and N=150, 24 sites: microbial C:N, soil organic (Cs) C:N, residue C:N in layers 1-2, and their dependence on mineral N concentration.
SI.14: microbial C:N between 8.5 and 11.25 by residue C:N and mineral N. The engine uses 9.7 (microbial) and 9.4 (soil organic)."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"; rows=[]
    for r in rd(d+"dailySoilLayersCN.csv")[::5]:
        try: rows.append((N,int(r['date'][5:7]),float(r['microbial_C:N.1']),float(r['microbial_C:N.2']),float(r['soil_organic_C:N.1']),float(r['soil_organic_C:N.2']),float(r['residue_C:N.1']),float(r['NO3.1'])+float(r['NH4.1']),float(r['NO3.2'])+float(r['NH4.2'])))
        except (KeyError,ValueError): pass
    shutil.rmtree(d,ignore_errors=True); return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150)]),[])); np.save('/tmp/w/cycles_cn.npy',A); print(len(A),'samples')
    N,mo,mc1,mc2,sc1,sc2,rc1,c1,c2=A.T
    for n in (0,150):
        k=N==n; print(f'N={n}: microbial C:N layer1 mean {mc1[k].mean():.2f} sd {mc1[k].std():.2f} range {mc1[k].min():.2f}-{mc1[k].max():.2f} | layer2 mean {mc2[k].mean():.2f} | soil organic C:N layer1 mean {sc1[k].mean():.2f} sd {sc1[k].std():.2f} | layer 2 {sc2[k].mean():.2f}')
    k=rc1>1
    print('microbial C:N layer 1 by residue C:N (layer 1) and mineral N concentration (mg/kg):')
    for rlo,rhi in ((0,45),(45,70),(70,120)):
        out=[]
        for clo,chi in ((0,2),(2,6),(6,20),(20,500)):
            kk=k&(rc1>=rlo)&(rc1<rhi)&(c1>=clo)&(c1<chi)
            out.append(f'{mc1[kk].mean():.2f}(n{kk.sum()})' if kk.sum()>30 else 'na')
        print(f'  residue C:N {rlo}-{rhi}: mineral N 0-2/2-6/6-20/20+: '+'  '.join(out))
