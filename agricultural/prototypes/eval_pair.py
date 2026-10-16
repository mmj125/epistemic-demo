"""Paired held-out comparison of engine configurations on the 268-site set (2026-10-15). Usage: BASE=tag EXCL=train.json python3 eval_pair.py CAND...
Sites in EXCL (the optimizer's training sites) are dropped. Reports overall and per-N change in per-site MAE with a paired bootstrap, at g=1 and with g chosen on one half and applied to the other."""
import sys,os,json,glob,numpy as np
def load(tag):
    D={}
    for f in glob.glob(f'/tmp/w/{tag}_*_[0-9].json'):D.update(json.load(open(f)))
    return D
B=load(os.environ['BASE']);ex=set(json.load(open(os.environ['EXCL']))) if os.environ.get('EXCL') else set()
sites=sorted(set(k.split('|')[0] for k in B)-ex);Ns=(0,150,400)
pr=lambda D,s,N:np.array(D[f'{s}|N{N}|leadin']['res']['grain']['pairs'])
def mae(D,s,N,g=1.0):p=pr(D,s,N);return np.abs(p[:,1]*g-p[:,0]).mean()
rng=np.random.default_rng(0);half=np.arange(len(sites))%2==0;gs=np.arange(0.85,1.2,0.01)
def bestg(D,mask):return gs[np.argmin([np.mean([np.mean([mae(D,s,N,g) for N in Ns]) for s,m in zip(sites,mask) if m]) for g in gs])]
def boot(d,a):
    ii=rng.integers(0,len(d),(4000,len(d)));b=100*d[ii].mean(1)/a[ii].mean(1);return np.percentile(b,[2.5,97.5])
print('held-out sites',len(sites))
for tag in sys.argv[1:]:
    C=load(tag)
    for label in ('g=1','g fit on other half'):
        out=[]
        for Nset,name in ((Ns,'all'),((0,),'N0'),((150,),'N150'),((400,),'N400')):
            a=[];c=[]
            for m in (half,~half):
                gB=1.0 if label=='g=1' else bestg(B,m);gC=1.0 if label=='g=1' else bestg(C,m)
                for s,mm in zip(sites,m):
                    if not mm:a.append(np.mean([mae(B,s,N,gB) for N in Nset]));c.append(np.mean([mae(C,s,N,gC) for N in Nset]))
            a=np.array(a);c=np.array(c);d=c-a;lo,hi=boot(d,a)
            out.append('%s %+.1f%% [%+.1f,%+.1f] %d/%d'%(name,100*d.mean()/a.mean(),lo,hi,(d<0).sum(),len(d)))
        print(tag,label,'|',' | '.join(out))
