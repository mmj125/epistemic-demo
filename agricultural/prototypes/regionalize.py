"""Parameter regionalization on the scaled-up set (2026-10-15).
Step 1: for each site, find the net-N supply multiplier m in [0.6,1.4] and grain factor g in [0.8,1.25] that minimize the pooled N=0/150/400 per-year MAE against Cycles, interpolating the engine's per-year grain between runs at m = 0.7, 1.0, 1.4 (quadratic).
Step 2: learn (log m, log g) from site covariates with out-of-fold predictions (5-fold), then score the out-of-fold prediction on the same per-year pairs.
Usage: python3 regionalize.py   (needs runs base2, nm07, nm14)"""
import sys,json,glob,pickle,numpy as np
sys.path.insert(0,'.')
import field_data as fd
def load(tag):
    D={}
    for f in glob.glob(f'/tmp/w/{tag}_*_[0-9].json'):D.update(json.load(open(f)))
    return D
import os
TB,TL,TH=os.environ.get('TAGS','base2,nm07,nm14').split(',')
B,L,H=load(TB),load(TL),load(TH)
sites=sorted(set(k.split('|')[0] for k in B));Ns=(0,150,400)
def pairs(D,s,N):return np.array(D[f'{s}|N{N}|leadin']['res']['grain']['pairs'])   # [Cycles, engine]
M=np.linspace(0.6,1.4,17);G=np.linspace(0.8,1.25,19)
def interp(s,N,m):
    y0,y1,y2=pairs(L,s,N)[:,1],pairs(B,s,N)[:,1],pairs(H,s,N)[:,1]
    # quadratic through (0.7,y0),(1.0,y1),(1.4,y2)
    x=np.array([0.7,1.0,1.4]);out=[]
    for a,b,c in zip(y0,y1,y2):
        co=np.polyfit(x,[a,b,c],2);out.append(max(0.0,np.polyval(co,m)))
    return np.array(out)
def site_cost(s,m,g,N):
    pr=pairs(B,s,N);return np.abs(g*interp(s,N,m)-pr[:,0]).mean()
best={}
for s in sites:
    C=np.zeros((len(M),len(G)))
    for i,m in enumerate(M):
        yy={N:interp(s,N,m) for N in Ns}
        for j,g in enumerate(G):
            C[i,j]=np.mean([np.abs(g*yy[N]-pairs(B,s,N)[:,0]).mean() for N in Ns])
    i,j=np.unravel_index(C.argmin(),C.shape);best[s]=(M[i],G[j],C[i,j],C[M.tolist().index(1.0) if 1.0 in M.tolist() else 8,list(np.round(G,3)).index(1.0) if 1.0 in np.round(G,3) else 0])
J0=np.mean([np.mean([np.abs(pairs(B,s,N)[:,1]-pairs(B,s,N)[:,0]).mean() for N in Ns]) for s in sites])
Jo=np.mean([best[s][2] for s in sites])
print('baseline J %.4f   per-site-optimal (m,g) J %.4f  (upper bound %.1f%%)'%(J0,Jo,100*(J0-Jo)/J0))
m_=np.array([best[s][0] for s in sites]);g_=np.array([best[s][1] for s in sites]);print('optimal m: mean %.2f sd %.2f ; g: mean %.3f sd %.3f'%(m_.mean(),m_.std(),g_.mean(),g_.std()))
pickle.dump((sites,best),open('/tmp/w/regionalize_best'+os.environ.get('PK','')+'.pkl','wb'))
