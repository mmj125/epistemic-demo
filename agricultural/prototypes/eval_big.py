"""Evaluate a scaled-up run (base tag, e.g. 'o2'): pooled MAE by N, split into odd/even sites as pseudo train/test, plus bias-vs-clay and bias-vs-temperature slopes (2026-10-15). Usage: python3 eval_big.py TAG [TAG...]"""
import sys,json,glob,numpy as np
sys.path.insert(0,'.')
import field_data as fd
def load(tag):
    D={}
    for f in glob.glob(f'/tmp/w/{tag}_*_[0-9].json'):D.update(json.load(open(f)))
    if not D:
        for f in glob.glob(f'/tmp/w/{tag}_[0-9]*.json'):D.update(json.load(open(f)))
    return D
S={}
for sj in ('big240','old28'):S.update({k:tuple(v) for k,v in json.load(open(f'/tmp/w/{sj}.json')).items()})
import os,pickle
cp='/tmp/w/covcache.pkl'
if os.path.exists(cp):C=pickle.load(open(cp,'rb'))
else:
    C={}
    for s,(lat,lon) in S.items():
        wx,_=fd.resolve_field_weather(lat,lon);soil,_,_=fd.resolve_field_soil(lat,lon);ys=sorted(wx)
        gt=np.mean([np.mean([(r['tx']+r['tn'])/2 for d,r in wx[y].items() if 121<=d<=273]) for y in ys])
        top=soil[:3];C[s]=(gt,np.mean([l['clay'] for l in top]))
    pickle.dump(C,open(cp,'wb'))
for tag in sys.argv[1:]:
    D=load(tag);sites=sorted(set(k.split('|')[0] for k in D));g=lambda s,N,v:D[f'{s}|N{N}|leadin']['res'][v]
    print('== %s  sites %d'%(tag,len(sites)))
    for N in (0,150,400):
        if f'{sites[0]}|N{N}|leadin' not in D:continue
        a=np.array([g(s,N,'grain')['mae'] for s in sites]);b=np.array([g(s,N,'grain')['model']-g(s,N,'grain')['real'] for s in sites])
        c=np.array([g(s,N,'grain')['corr'] for s in sites]);c=np.nanmean(c)
        clay=np.array([C[s][1] for s in sites]);gt=np.array([C[s][0] for s in sites])
        print('  N=%3d MAE %.3f (odd %.3f even %.3f) corr %.3f bias %+.3f | bias slope per 10%% clay %+.2f, per 1C gs-temp %+.2f'%(N,a.mean(),a[0::2].mean(),a[1::2].mean(),c,b.mean(),10*np.polyfit(clay,b,1)[0],np.polyfit(gt,b,1)[0]))
