"""Site-mean grain bias (engine minus Cycles) versus site covariates, 94 fresh sites, per N rate: leave-one-site-out R2 of a ridge regression and standardized coefficients (2026-10-17). Covariates: growing-season (DOY 121-273) mean temperature, precipitation, solar, VPD proxy (tx-tn), topsoil clay, sand, SOC, profile depth, latitude. Usage: python3 corn_bias_covariates_2026_10_17.py TAG"""
import sys,json,glob,pickle,os,numpy as np
sys.path.insert(0,'.')
import field_data as fd
tag=sys.argv[1] if len(sys.argv)>1 else "L"
D={}
for f in glob.glob(f'/tmp/w/fr{tag}_[0-3].json'): D.update(json.load(open(f)))
S=json.load(open('sitesets/fresh94.json')); sites=sorted(set(k.split('|')[0] for k in D))
cp='/tmp/w/cov94.pkl'
if os.path.exists(cp): C=pickle.load(open(cp,'rb'))
else:
    C={}
    for s in sites:
        lat,lon=S[s]; wx,_=fd.resolve_field_weather(lat,lon); soil,_,_=fd.resolve_field_soil(lat,lon); ys=sorted(wx); top=soil[:3]
        def gs(f): return np.mean([np.mean([f(r) for d,r in wx[y].items() if 121<=d<=273]) for y in ys])
        C[s]=[gs(lambda r:(r['tx']+r['tn'])/2),gs(lambda r:r['pp'])*153,gs(lambda r:r['solar']),gs(lambda r:r['tx']-r['tn']),np.mean([l['clay'] for l in top]),np.mean([l['sand'] for l in top]),np.mean([l['soc'] for l in top]),sum(l['thick'] for l in soil),lat]
    pickle.dump(C,open(cp,'wb'))
names=["gs temp","gs precip","gs solar","diurnal range","clay","sand","SOC","profile depth","latitude"]
X=np.array([C[s] for s in sites]); Xs=(X-X.mean(0))/X.std(0)
def ridge(X,y,l=3.0): return np.linalg.solve(X.T@X+l*np.eye(X.shape[1]),X.T@y)
for N in (0,150,400):
    y=np.array([np.mean(np.array(D[f'{s}|N{N}|leadin']['res']['grain']['pairs'])[:,1]-np.array(D[f'{s}|N{N}|leadin']['res']['grain']['pairs'])[:,0]) for s in sites])
    yc=y-y.mean(); pred=np.zeros(len(y))
    for i in range(len(y)):
        m=np.ones(len(y),bool); m[i]=False; b=ridge(Xs[m],yc[m]); pred[i]=Xs[i]@b
    r2=1-((yc-pred)**2).sum()/(yc**2).sum(); b=ridge(Xs,yc)
    print(f"N={N}: site-mean bias sd {y.std():.2f}, leave-one-out R2 {r2:.2f}; coefficients (Mg/ha per sd): "+", ".join(f"{n} {c:+.2f}" for n,c in sorted(zip(names,b),key=lambda t:-abs(t[1]))[:5]))
