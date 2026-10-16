import glob,numpy as np,sys
from scipy.optimize import least_squares
F=sorted(glob.glob('/tmp/w/nlaw/*.npz')); D=[]
for f in F:
    z=np.load(f); n=len(z['denitrification'])
    L=z['theta'].shape[1]
    rel=np.clip(z['theta']/z['sat'][:L],0,1.2); T=np.maximum(z['tsoil'][:,:L],0)
    D.append(dict(site=f.split('/')[-1][:-4],y=z['denitrification'],no3=z['no3_l'][:,:L],rel=rel,T=T,fcrel=np.clip((z['theta']-z['pwp'][:L])/(z['fc'][:L]-z['pwp'][:L]),0,3)))
tr=[d for i,d in enumerate(D) if i%2==0]; te=[d for i,d in enumerate(D) if i%2==1]
def pred(d,p,kind):
    k,pw,q=np.exp(p[0]),p[1],p[2]
    if kind=='L1': return d['no3'][:,0]*k*d['rel'][:,0]**pw*d['T'][:,0]**q
    if kind=='ALL': return (d['no3']*k*d['rel']**pw*d['T']**q).sum(1)
    if kind=='ALLfc':
        return (d['no3']*k*d['fcrel']**pw*d['T']**q).sum(1)
def fit(kind):
    f=lambda p:np.concatenate([pred(d,p,kind)-d['y'] for d in tr])
    r=least_squares(f,[np.log(1e-3),5,1.0]); return r.x
def score(ds,p,kind):
    ys=np.concatenate([d['y'] for d in ds]); ps=np.concatenate([pred(d,p,kind) for d in ds])
    r2=1-((ys-ps)**2).sum()/((ys-ys.mean())**2).sum()
    # site totals per site-run
    a=np.array([d['y'].sum()/37 for d in ds]);b=np.array([pred(d,p,kind).sum()/37 for d in ds])
    ok=(a>0.05)
    rms=np.sqrt(np.mean((np.log((b[ok]+0.05)/(a[ok]+0.05)))**2))
    return r2,rms,np.mean(b)/np.mean(a)
for kind in ('L1','ALL','ALLfc'):
    p=fit(kind); print(kind,'params k=%.4g pw=%.2f q=%.2f'%(np.exp(p[0]),p[1],p[2]),'train R2/rmslog/ratio',tuple(round(x,2) for x in score(tr,p,kind)),'TEST',tuple(round(x,2) for x in score(te,p,kind)))
