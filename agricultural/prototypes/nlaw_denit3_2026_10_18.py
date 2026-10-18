"""Denitrification structure test on Cycles' own daily states (2026-10-18). The Cycles guide lists POT_DENITRIF_RATE (kg N per kg soil per day) and
DENITRIF_HALF_RATE (half saturation), so nitrate enters as a Michaelis-Menten term in CONCENTRATION, per layer. Compare per-layer forms against the engine's
current total-nitrate x respiration law (nlaw_denit2.py 'resp'), same even/odd site split, daily R2 and site-total rms log error."""
import glob,numpy as np
from scipy.optimize import least_squares
D=[]
for f in sorted(glob.glob('/tmp/w/nlaw/*.npz')):
    z=np.load(f); n=len(z['denitrification']); bd=z['bd']; th=z['thick']; mass=bd*th*1e4   # Mg soil per ha per layer
    conc=z['no3_l']/(bd*th*10)                                                                 # mg N/kg soil
    rel=np.clip(z['theta']/z['sat'][None,:],0.02,1.2)
    D.append(dict(site=f.split('/')[-1][:-4],y=z['denitrification'],conc=conc,rel=rel,T=np.maximum(z['tsoil'],0.0),mass=mass,no3=z['no3_l']))
tr=[d for i,d in enumerate(D) if i%2==0]; te=[d for i,d in enumerate(D) if i%2==1]
def pred(d,p,kind):
    k=np.exp(p[0]); c=d['conc']; r=d['rel']; T=d['T']; M=d['mass'][None,:]
    mm=c/(c+np.exp(p[1]))
    if kind=='MM_pow_T':  return (k*M*mm*r**p[2]*(T/20.0)**p[3]).sum(1)
    if kind=='MM_hill_T': h=p[3]; return (k*M*mm*(r**p[2]/(r**p[2]+h**p[2]))*(T/20.0)**p[4]).sum(1)
    if kind=='MM_pow_exp':return (k*M*mm*r**p[2]*np.exp(p[3]*(T-20.0)/10.0)).sum(1)
    if kind=='layer1_MM_pow_T': return (k*M[:,0]*mm[:,0]*r[:,0]**p[2]*(T[:,0]/20.0)**p[3])
def fit(kind,p0):
    return least_squares(lambda p:np.concatenate([pred(d,p,kind)-d['y'] for d in tr]),p0,max_nfev=400).x
def score(ds,p,kind):
    ys=np.concatenate([d['y'] for d in ds]); ps=np.concatenate([pred(d,p,kind) for d in ds]); r2=1-((ys-ps)**2).sum()/((ys-ys.mean())**2).sum()
    a=np.array([d['y'].sum()/37 for d in ds]); b=np.array([pred(d,p,kind).sum()/37 for d in ds]); ok=a>0.05
    return 'R2 %.2f  site-total rms log %.2f  ratio %.2f'%(r2,np.sqrt(np.mean(np.log((b[ok]+.05)/(a[ok]+.05))**2)),b.mean()/a.mean())
for kind,p0 in (('MM_pow_T',[np.log(1e-5),np.log(5),6,1]),('MM_pow_exp',[np.log(1e-5),np.log(5),6,0.5]),('MM_hill_T',[np.log(1e-5),np.log(5),6,0.8,1]),('layer1_MM_pow_T',[np.log(1e-5),np.log(5),6,1])):
    p=fit(kind,p0); print('%-16s'%kind,np.round(p,3),'\n     train',score(tr,p,kind),'\n     TEST ',score(te,p,kind))
