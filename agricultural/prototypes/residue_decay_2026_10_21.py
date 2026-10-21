import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/resdata.npy'); Z=np.load('/tmp/w/site_l1.npz')
site=A[:,0].astype(int); doy=A[:,2]; rres=A[:,3]; rsom=A[:,4]; ab=A[:,5]; bel=A[:,6]; root=A[:,7]; ms=A[:,8]; mf=A[:,9]; T=A[:,10]; th=A[:,11]
tot=ab+bel+root
print("rows",len(A),"mean residue biomass",tot.mean(),"mean resid resp",rres.mean())
same=np.zeros(len(A),bool); same[1:]=(site[1:]==site[:-1])&(doy[1:]-doy[:-1]==1)
prev=lambda a: np.concatenate([[0],a[:-1]])
rate=rres/np.maximum(tot,1e-6)
sub=same&(tot>1.0)&(T>0)&(np.random.default_rng(0).random(len(A))<0.5)
def fT(Tv,To=36.1,c=2.18): t=Tv+c;o=To+c; return np.clip((2*t*t*o*o-t**4)/o**4,0,1)
PW=Z['pwp'][site]; FC=Z['fc'][site]; rel=np.clip((prev(th)-PW)/np.maximum(FC-PW,1e-3),0,None)
def run(nm,mv,use_flat_only=False):
    f=lambda p:p[0]*fT(T)*(np.clip(mv,1e-6,None)**abs(p[2])/(np.clip(mv,1e-6,None)**abs(p[2])+abs(p[1])**abs(p[2])))
    r=least_squares(lambda p:(f(p)-rate)[sub],[0.01,0.2,2],max_nfev=400); pp=f(r.x)
    print(f" {nm:44s} R2 {1-((rate-pp)[sub]**2).sum()/((rate[sub]-rate[sub].mean())**2).sum():.3f}",np.round(r.x,4))
run("soil relwet (start of day)",rel)
run("flat residue moisture (start of day)",prev(mf))
run("flat residue moisture (today)",mf)
run("standing residue moisture (start of day)",prev(ms))
# surface share: how is residue split?
print("mean shares above/below/root:",ab.mean()/tot.mean(),bel.mean()/tot.mean(),root.mean()/tot.mean())
print("moisture ranges flat",np.percentile(mf,[5,50,95]),"standing",np.percentile(ms,[5,50,95]))
