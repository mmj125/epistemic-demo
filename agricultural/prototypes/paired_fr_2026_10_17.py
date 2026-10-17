"""Paired site-MAE comparison on the 94 fresh sites (split in four files /tmp/w/fr<TAG>_<i>.json): base TAG minus new TAG, mean site MAE (Mg/ha) by N with 95% bootstrap CI, bias, sites improved. Usage: python3 paired_fr_2026_10_17.py BASE NEW [NEW...]"""
import sys,json,glob,numpy as np
def load(tag):
    D={}
    for f in glob.glob(f'/tmp/w/fr{tag}_[0-3].json'):D.update(json.load(open(f)))
    return D
def site(D,s,N):
    p=np.array(D[f'{s}|N{N}|leadin']['res']['grain']['pairs']); return np.abs(p[:,1]-p[:,0]).mean(),(p[:,1]-p[:,0]).mean()
B=load(sys.argv[1]); sites=sorted(set(k.split('|')[0] for k in B)); rng=np.random.default_rng(0); idx=rng.integers(0,len(sites),(4000,len(sites)))
for tag in sys.argv[2:]:
    D=load(tag)
    if not D: print(tag,"missing"); continue
    ss=[s for s in sites if all(f'{s}|N{N}|leadin' in D for N in (0,150,400))]
    print(f"{tag} vs {sys.argv[1]} ({len(ss)} sites)")
    for N in (0,150,400):
        b=np.array([site(B,s,N)[0] for s in ss]); n=np.array([site(D,s,N)[0] for s in ss]); d=b-n
        bb=np.array([site(B,s,N)[1] for s in ss]).mean(); nb=np.array([site(D,s,N)[1] for s in ss]).mean()
        i2=rng.integers(0,len(ss),(4000,len(ss))); bt=d[i2].mean(1)
        print(f"  N={N}: MAE base {b.mean():.3f} new {n.mean():.3f}  gain {d.mean():+.3f} [{np.percentile(bt,2.5):+.3f},{np.percentile(bt,97.5):+.3f}]  bias {bb:+.2f} -> {nb:+.2f}  sites improved {(d>0).sum()}/{len(ss)}")
