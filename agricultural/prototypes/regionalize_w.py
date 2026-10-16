"""Third regional parameter (REFIT_PLAN row 45): per-site grain factor g and water-use-efficiency multiplier w, found from engine runs at w = 0.85 / 1.0 / 1.15
(quadratic interpolation per site-year), then predicted out-of-fold from six covariates. Usage: python3 regionalize_w.py (needs runs st3b, wl, wh)"""
import sys,json,glob,pickle,os,numpy as np
sys.path.insert(0,'.')
def load(tag):
    D={}
    for f in glob.glob(f'/tmp/w/{tag}_*_[0-9].json'):D.update(json.load(open(f)))
    return D
B,L,H=load('st3b'),load('wl'),load('wh');sites=sorted(set(k.split('|')[0] for k in B));Ns=(0,150,400)
pr=lambda D,s,N:np.array(D[f'{s}|N{N}|leadin']['res']['grain']['pairs'])
Wg=np.linspace(0.85,1.15,13);G=np.linspace(0.8,1.25,19)
def y_at(s,N,w):
    y0,y1,y2=pr(L,s,N)[:,1],pr(B,s,N)[:,1],pr(H,s,N)[:,1];x=np.array([0.85,1.0,1.15]);out=[]
    for a,b,c in zip(y0,y1,y2):
        co=np.polyfit(x,[a,b,c],2);out.append(max(0.0,np.polyval(co,w)))
    return np.array(out)
best={};bestg={}
for s in sites:
    C=np.zeros((len(Wg),len(G)))
    for i,w in enumerate(Wg):
        yy={N:y_at(s,N,w) for N in Ns}
        for j,g in enumerate(G):C[i,j]=np.mean([np.abs(g*yy[N]-pr(B,s,N)[:,0]).mean() for N in Ns])
    i,j=np.unravel_index(C.argmin(),C.shape);best[s]=(Wg[i],G[j],C[i,j])
    i1=list(np.round(Wg,3)).index(1.0);jj=C[i1].argmin();bestg[s]=(1.0,G[jj],C[i1,jj])
J0=np.mean([np.mean([np.abs(pr(B,s,N)[:,1]-pr(B,s,N)[:,0]).mean() for N in Ns]) for s in sites])
print('baseline J %.4f | g-only per-site optimum %.4f | g+w per-site optimum %.4f (extra upper bound %.1f%%)'%(J0,np.mean([bestg[s][2] for s in sites]),np.mean([best[s][2] for s in sites]),100*(np.mean([bestg[s][2] for s in sites])-np.mean([best[s][2] for s in sites]))/np.mean([bestg[s][2] for s in sites])))
w_=np.array([best[s][0] for s in sites]);print('optimal w: mean %.3f sd %.3f'%(w_.mean(),w_.std()))
cp='/tmp/w/cov2.pkl';X=pickle.load(open(cp,'rb'));XX=np.array([X[s] for s in sites])
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold
lw=np.log([best[s][0] for s in sites]);lg=np.log([best[s][1] for s in sites]);lg1=np.log([bestg[s][1] for s in sites])
def oof(y,seed=0):
    p=np.zeros(len(y))
    for tr,te in KFold(5,shuffle=True,random_state=seed).split(XX):p[te]=GradientBoostingRegressor(n_estimators=120,max_depth=2,learning_rate=0.05,subsample=0.8,random_state=0).fit(XX[tr],y[tr]).predict(XX[te])
    return p
for seed in (0,1):
    pg1=np.clip(np.exp(oof(lg1,seed)),0.8,1.25)
    pw=np.clip(np.exp(oof(lw,seed)),0.85,1.15);pg=np.clip(np.exp(oof(lg,seed)),0.8,1.25)
    s1=np.mean([np.mean([np.abs(pg1[k]*pr(B,s,N)[:,1]-pr(B,s,N)[:,0]).mean() for N in Ns]) for k,s in enumerate(sites)])
    s2=np.mean([np.mean([np.abs(pg[k]*y_at(s,N,pw[k])-pr(B,s,N)[:,0]).mean() for N in Ns]) for k,s in enumerate(sites)])
    r2=lambda y,p:1-((y-np.log(p))**2).sum()/((y-y.mean())**2).sum()
    print('seed',seed,'out-of-fold J g-only %.4f | g+w %.4f (%.1f%% better) | R2 log w %.2f'%(s1,s2,100*(s1-s2)/s1,r2(lw,pw)))
pickle.dump((sites,best),open('/tmp/w/regionalize_w_best.pkl','wb'))
