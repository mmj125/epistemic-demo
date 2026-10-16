"""Paired per-site significance of each candidate against the baseline on the 268-site set, with a global grain re-centering per configuration (2026-10-15). Usage: python3 paired_sig.py TAG [TAG...]"""
import sys,json,glob,numpy as np
def load(tag):
    D={}
    for f in glob.glob(f'/tmp/w/{tag}_*_[0-9].json'):D.update(json.load(open(f)))
    return D
import os
B=load(os.environ.get('BASE','base2'));sites=sorted(set(k.split('|')[0] for k in B));Ns=(0,150,400)
def pairs(D,s,N):return np.array(D[f'{s}|N{N}|leadin']['res']['grain']['pairs'])
def sitej(D,g):return np.array([np.mean([np.abs(pairs(D,s,N)[:,1]*g-pairs(D,s,N)[:,0]).mean() for N in Ns]) for s in sites])
def best(D):
    gs=np.arange(0.85,1.16,0.01);return gs[np.argmin([sitej(D,g).mean() for g in gs])]
jb=sitej(B,1.0);rng=np.random.default_rng(0);idx=rng.integers(0,len(sites),(4000,len(sites)))
print('baseline J %.4f   tag: best global factor, mean change %%, 95%% CI, sites improved'%jb.mean())
for tag in sys.argv[1:]:
    D=load(tag)
    if not D:continue
    g=best(D);jc=sitej(D,g);d=jc-jb;boot=(d[idx].mean(1)/jb[idx].mean(1))*100
    print('%-8s g %.2f  %+.2f%%  CI [%+.2f, %+.2f]  sites improved %d/%d'%(tag,g,100*d.mean()/jb.mean(),np.percentile(boot,2.5),np.percentile(boot,97.5),(d<0).sum(),len(d)))
