"""Evaluate scaled-up runs with a single global grain re-centering factor per configuration (grid 0.85-1.15 on the mean of the per-N pooled MAE), train/test split by site index, and the slope diagnostics (2026-10-15). Needs runs made after the pairs field was added. Usage: python3 eval_big2.py TAG [TAG ...]   (TAG 'base2' = baseline)"""
import sys,json,glob,numpy as np,pickle
C=pickle.load(open('/tmp/w/covcache.pkl','rb'))
def load(tag):
    D={}
    for f in glob.glob(f'/tmp/w/{tag}_*_[0-9].json'):D.update(json.load(open(f)))
    return D
def evalcfg(D,sites,Ns,g):
    out={}
    for N in Ns:
        mae=[];bias=[]
        for s in sites:
            pr=np.array(D[f'{s}|N{N}|leadin']['res']['grain']['pairs']);mae.append(np.abs(pr[:,1]*g-pr[:,0]).mean());bias.append((pr[:,1]*g-pr[:,0]).mean())
        out[N]=(np.mean(mae),np.mean(bias))
    return out
for tag in sys.argv[1:]:
    D=load(tag);sites=sorted(set(k.split('|')[0] for k in D))
    Ns=[N for N in (0,150,400) if f'{sites[0]}|N{N}|leadin' in D and 'pairs' in D[f'{sites[0]}|N{N}|leadin']['res']['grain']]
    # train = even-indexed sites, test = odd-indexed; g chosen on train
    tr=sites[0::2];te=sites[1::2]
    best=min(np.arange(0.85,1.16,0.01),key=lambda g:np.mean([v[0] for v in evalcfg(D,tr,Ns,g).values()]))
    r1=evalcfg(D,tr,Ns,1.0);rb=evalcfg(D,tr,Ns,best);t1=evalcfg(D,te,Ns,1.0);tb=evalcfg(D,te,Ns,best)
    J=lambda r:np.mean([v[0] for v in r.values()])
    print('== %s  sites %d  Ns %s  global grain factor chosen on train: %.2f'%(tag,len(sites),Ns,best))
    print('   train J %.4f -> %.4f   test J %.4f -> %.4f   (J = mean over N of mean per-site MAE)'%(J(r1),J(rb),J(t1),J(tb)))
    print('   test per-N MAE (re-centered): '+'  '.join('N=%d %.3f (bias %+.2f)'%(N,tb[N][0],tb[N][1]) for N in Ns))
