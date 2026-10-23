"""Metrics beyond pooled r (2026-10-23), from the cur_* run files (94 fresh sites): pooled r, Lin's CCC, Nash-Sutcliffe, site-mean r, within-site r, within-site anomaly r and sd ratio, share of sites with negative bias,
bias by yield tercile, and the engine's N response (0 to 150, 150 to 400) against Cycles'. Usage: python3 metrics_panel_2026_10_23.py corn=cur_corn silage=cur_silage sorghum=cur_sorghum"""
import json,glob,sys,numpy as np
def load(pre):
    D={}
    for f in glob.glob(f'/tmp/w/{pre}_[0-3].json'): D.update(json.load(open(f)))
    return D
ccc=lambda x,y:2*np.cov(x,y,bias=True)[0,1]/(x.var()+y.var()+(x.mean()-y.mean())**2)
for arg in sys.argv[1:] or ["corn=cur_corn","silage=cur_silage","sorghum=cur_sorghum"]:
    crop,pre=arg.split("="); D=load(pre); sites=sorted({k.split('|')[0] for k in D}); P={}
    print("=====",crop)
    for n in (0,150,400):
        P[n]={s:np.array(D[f"{s}|N{n}|leadin"]["res"]["grain"]["pairs"]) for s in sites if f"{s}|N{n}|leadin" in D}
        allp=np.vstack(list(P[n].values())); c,e=allp[:,0],allp[:,1]
        sb=np.array([(p[:,1]-p[:,0]).mean() for p in P[n].values()]); sm=np.array([p[:,0].mean() for p in P[n].values()]); em=np.array([p[:,1].mean() for p in P[n].values()])
        wr=np.array([np.corrcoef(p[:,0],p[:,1])[0,1] for p in P[n].values() if p[:,0].std()>0 and p[:,1].std()>0])
        ca=np.concatenate([p[:,0]-p[:,0].mean() for p in P[n].values()]); ea=np.concatenate([p[:,1]-p[:,1].mean() for p in P[n].values()])
        t=np.percentile(sm,[0,33,66,100])
        print(f"N={n}: pooled r {np.corrcoef(c,e)[0,1]:.3f} CCC {ccc(c,e):.3f} NSE {1-((e-c)**2).sum()/((c-c.mean())**2).sum():.3f} site-mean r {np.corrcoef(sm,em)[0,1]:.3f} within-site r median {np.median(wr):.2f} anomaly r {np.corrcoef(ca,ea)[0,1]:.2f} anomaly sd ratio {ea.std()/ca.std():.2f} negative-bias sites {100*(sb<0).mean():.0f}% bias by tercile "+" ".join(f"{sb[(sm>=a)&(sm<=b)].mean():+.2f}" for a,b in zip(t[:-1],t[1:])))
    for a,b in ((0,150),(150,400)):
        dc=[];de=[]
        for s in sites:
            if s in P[a] and s in P[b] and len(P[a][s])==len(P[b][s]): dc+=list(P[b][s][:,0]-P[a][s][:,0]); de+=list(P[b][s][:,1]-P[a][s][:,1])
        dc,de=np.array(dc),np.array(de); print(f"  N response {a}->{b}: Cycles {dc.mean():.2f} engine {de.mean():.2f} Mg/ha ({100*de.mean()/dc.mean():.0f}%), site-year response r {np.corrcoef(dc,de)[0,1]:.2f}")
