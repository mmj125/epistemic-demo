import glob,csv,numpy as np
from scipy.optimize import least_squares
D=[]
for f in sorted(glob.glob('/tmp/w/nlaw/*.npz')):
    z=np.load(f); site=f.split('/')[-1][:-4]; n=len(z['denitrification'])
    r=list(csv.reader(open(f'/tmp/cycles-run15/output/{site}/dailySoilC.csv')))[2:][:n]
    resp=np.array([float(x[3])+float(x[4]) for x in r]); L=z['theta'].shape[1]
    D.append(dict(site=site,y=z['denitrification'],no3=z['no3_l'].sum(1),no3_1=z['no3_l'][:,0],rel1=np.clip(z['theta'][:,0]/z['sat'][0],0.02,1.2),resp=resp*1000+1e-3,T=np.maximum(z['tsoil'][:,0],0)))  # resp in kg C/ha
tr=[d for i,d in enumerate(D) if i%2==0]; te=[d for i,d in enumerate(D) if i%2==1]
def pred(d,p,kind):
    k=np.exp(p[0])
    if kind=='base': return d['no3_1']*k*d['rel1']**p[1]*d['T']**p[2]
    if kind=='resp': return k*d['no3']**p[2]*d['resp']**p[3]*d['rel1']**p[1]
    if kind=='respMM': return k*d['no3']/(d['no3']+np.exp(p[2]))*d['resp']**p[3]*d['rel1']**p[1]
def fit(kind,p0):
    r=least_squares(lambda p:np.concatenate([pred(d,p,kind)-d['y'] for d in tr]),p0,max_nfev=300); return r.x
def score(ds,p,kind):
    ys=np.concatenate([d['y'] for d in ds]); ps=np.concatenate([pred(d,p,kind) for d in ds])
    r2=1-((ys-ps)**2).sum()/((ys-ys.mean())**2).sum()
    a=np.array([d['y'].sum()/37 for d in ds]);b=np.array([pred(d,p,kind).sum()/37 for d in ds]); ok=a>0.05
    return round(r2,2),round(float(np.sqrt(np.mean(np.log((b[ok]+.05)/(a[ok]+.05))**2))),2),round(b.mean()/a.mean(),2)
for kind,p0 in (('base',[np.log(1e-3),6,1]),('resp',[np.log(1e-5),2.6,0.6,0.85]),('respMM',[np.log(1e-3),2.6,np.log(20),0.85])):
    p=fit(kind,p0); print(kind,np.round(p,3),'train',score(tr,p,kind),'TEST',score(te,p,kind))
