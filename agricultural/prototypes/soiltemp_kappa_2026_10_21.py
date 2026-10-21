import numpy as np
from scipy.linalg import solve_banded
A=np.load('/tmp/w/ndata.npz')['A']; W=np.load('/tmp/w/ndata_wx.npz'); Z=np.load('/tmp/w/site_l1.npz')
site=A[:,9].astype(int); N0=A[:,0]==0
def L(k,j): return A[:,14+10*k+j]
def grid(dz0=0.02,zmax=3.0):
    h=[];z=0;w=dz0
    while z<zmax-1e-9: w=min(w,zmax-z); h.append(w); z+=w; w*=1.25
    return np.array(h)
H=grid(); n=len(H); mid=np.cumsum(H)-H/2
def run(air,Dfun,thick,tmean0):
    """Dfun(day)->array of n diffusivities (m2/day). implicit step, surface = air, bottom = running mean"""
    T=np.full(n,tmean0); tm=tmean0; out=[]
    edges=np.concatenate([[0],np.cumsum(thick)]); wts=[]
    for k in range(len(thick)):
        lo=np.clip(np.cumsum(H)-H,edges[k],edges[k+1]); hi=np.clip(np.cumsum(H),edges[k],edges[k+1]); w=np.clip(hi-lo,0,None); wts.append(w/w.sum() if w.sum()>0 else None)
    for d,t in enumerate(air):
        D=Dfun(d); tm+=(t-tm)/365.0
        Di=0.5*(D[1:]+D[:-1]); g=Di/(mid[1:]-mid[:-1]); gtop=D[0]/mid[0]; gbot=D[-1]/(3.0-mid[-1])
        gl=np.concatenate([[gtop],g]); gu=np.concatenate([g,[gbot]])
        ab=np.zeros((3,n)); ab[1]=1+(gl+gu)/H; ab[0,1:]=-gu[:-1]/H[:-1]; ab[2,:-1]=-gl[1:]/H[1:]
        rhs=T.copy(); rhs[0]+=gtop*t/H[0]; rhs[-1]+=gbot*tm/H[-1]
        T=solve_banded((1,1),ab,rhs)
        out.append([T@w if w is not None else tm for w in wts] if False else [float(np.dot(T,w)) if w is not None else tm for w in wts])
    return np.array(out)
def kappa(theta,bd,clay):
    """Campbell et al 1994 style conductivity (recollection) / heat capacity -> m2/day"""
    A_=0.65-0.78*bd+0.60*bd**2; B=1.06*bd; C=1+2.6/np.sqrt(max(clay,1.0)); D=0.03+0.1*bd**2
    lam=A_+B*theta-(A_-D)*np.exp(-(C*theta)**4)
    cv=2.0e6*(bd/2.65)+4.18e6*theta
    return lam/cv*86400.0
res={}
for s in range(24):
    k=(site==s)&N0
    if k.sum()<1000: continue
    air=((W['tx']+W['tn'])/2)[k]; Tc=np.column_stack([L(i,7)[k] for i in range(4)]); th=np.column_stack([L(i,5)[k] for i in range(4)]); thick=[L(i,8)[k][0] for i in range(4)]; bd=[L(i,9)[k][0] for i in range(4)]
    nl=sum(1 for t in thick if t>0); thick=thick[:nl]; yr=A[k,10]; ok=yr>=1982+3
    best=None
    for Dc in (0.03,0.05,0.08,0.12,0.2):
        o=run(air,lambda d,Dc=Dc:np.full(n,Dc),thick,air[:365].mean()); e=np.sqrt(np.mean((o[ok,:min(nl,3)]-Tc[ok,:min(nl,3)])**2))
        if best is None or e<best[1]: best=(Dc,e)
    clay=1.0
    # physical kappa from layer moisture, time varying; nodes inherit the layer containing them
    edges=np.concatenate([[0],np.cumsum(thick)]); lay=np.clip(np.searchsorted(edges,mid,side='right')-1,0,nl-1)
    clayv=30.0
    def Dphys(d,scale=1.0):
        return np.array([kappa(th[d,lay[j]],bd[lay[j]],clayv) for j in range(n)])*scale
    o=run(air,lambda d:Dphys(d),thick,air[:365].mean()); e_phys=np.sqrt(np.mean((o[ok,:min(nl,3)]-Tc[ok,:min(nl,3)])**2))
    kmean=np.mean([kappa(th[:,0].mean(),bd[0],clayv)])
    res[s]=(best[0],best[1],e_phys,kmean,th[:,0].mean())
    print(f"site {s:2d} best const D {best[0]:.2f} rms {best[1]:.2f} | physical kappa(theta_t) rms {e_phys:.2f} (mean kappa layer1 {kmean:.3f}) mean theta1 {th[:,0].mean():.3f}",flush=True)
    if s>=7: break
