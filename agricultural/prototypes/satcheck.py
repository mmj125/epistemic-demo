"""Does the soil carbon saturation ratio (SOC / clay-dependent capacity) explain the engine's per-site bias better than clay and SOC separately? (2026-10-15)"""
import sys,json,glob,numpy as np
sys.path.insert(0,'.')
import field_data as fd
D={}
for f in glob.glob('/tmp/w/base2_*_[0-9].json'):D.update(json.load(open(f)))
S={}
for sj in ('big240','old28'):S.update({k:tuple(v) for k,v in json.load(open(f'/tmp/w/{sj}.json')).items()})
sites=sorted(set(k.split('|')[0] for k in D))
rows=[]
for s in sites:
    soil,_,_=fd.resolve_field_soil(*S[s]);l=soil[0]
    clay=np.mean([x['clay'] for x in soil[:3]]);soc=np.mean([(x['soc'] or 0.2) for x in soil[:3]])
    csx=2.11+3.75*clay/100
    rows.append((clay,soc,soc/csx,soc/(2.11+3.75*clay/100)))
X=np.array(rows)
for N in (0,150,400):
    y=np.array([D[f'{s}|N{N}|leadin']['res']['grain']['model']-D[f'{s}|N{N}|leadin']['res']['grain']['real'] for s in sites])
    print('N=%d  corr(bias): clay %+.2f  soc %+.2f  saturation ratio %+.2f'%(N,np.corrcoef(X[:,0],y)[0,1],np.corrcoef(X[:,1],y)[0,1],np.corrcoef(X[:,2],y)[0,1]))
    q=np.quantile(X[:,2],np.linspace(0,1,6))
    print('   by saturation-ratio quintile: '+'  '.join('%.2f:%+.2f'%(X[(X[:,2]>=lo)&(X[:,2]<=hi),2].mean(),y[(X[:,2]>=lo)&(X[:,2]<=hi)].mean()) for lo,hi in zip(q[:-1],q[1:])))
