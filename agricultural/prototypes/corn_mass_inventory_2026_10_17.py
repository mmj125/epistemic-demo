"""Corn mass inventory (2026-10-17): from a 94-site run (/tmp/w/fr<TAG>_i.json), grain and total biomass error by N rate: pooled MAE/bias/correlation, split into site-mean bias and within-site (yearly) error, the share of squared error carried by failed site-years (engine below 30% of Cycles where Cycles is above 2 Mg/ha), error by Cycles yield tercile and by latitude band, and the harvest index implied by grain/biomass. Usage: python3 corn_mass_inventory_2026_10_17.py TAG"""
import sys,json,glob,numpy as np
tag=sys.argv[1] if len(sys.argv)>1 else "K"
D={}
for f in glob.glob(f'/tmp/w/fr{tag}_[0-3].json'): D.update(json.load(open(f)))
S=json.load(open('sitesets/fresh94.json'))
sites=sorted(set(k.split('|')[0] for k in D))
def P(s,N,v): return np.array(D[f'{s}|N{N}|leadin']['res'][v]['pairs'])
print(f"{tag}: {len(sites)} sites")
for v in ('grain','total_biomass'):
    for N in (0,150,400):
        allp=np.concatenate([P(s,N,v) for s in sites]); c,e=allp[:,0],allp[:,1]
        sm=np.array([ (P(s,N,v)[:,1]-P(s,N,v)[:,0]).mean() for s in sites])
        within=np.concatenate([ (P(s,N,v)[:,1]-P(s,N,v)[:,1].mean())-(P(s,N,v)[:,0]-P(s,N,v)[:,0].mean()) for s in sites])
        fail=(e<0.3*c)&(c>2.0); se=(e-c)**2
        cs=[np.corrcoef(P(s,N,v)[:,0],P(s,N,v)[:,1])[0,1] for s in sites if P(s,N,v)[:,0].std()>0 and P(s,N,v)[:,1].std()>0]
        print(f"{v:13s} N={N:3d}: Cycles mean {c.mean():6.2f} engine {e.mean():6.2f} MAE {np.abs(e-c).mean():.3f} ({100*np.abs(e-c).mean()/c.mean():.1f}%) | site-mean bias sd {sm.std():.2f} rms {np.sqrt((sm**2).mean()):.2f} | within-site rms {np.sqrt((within**2).mean()):.2f} mean corr {np.nanmean(cs):.2f} | failed site-years {fail.mean()*100:.1f}% carry {100*se[fail].sum()/se.sum():.0f}% of squared error")
# implied harvest index
for N in (0,150,400):
    g=np.concatenate([P(s,N,'grain') for s in sites]); b=np.concatenate([P(s,N,'total_biomass') for s in sites])
    print(f"N={N}: HI (grain/total) Cycles {g[:,0].sum()/b[:,0].sum():.3f} engine {g[:,1].sum()/b[:,1].sum():.3f}")
# by latitude band, grain N=150 and N=0 bias
lat={s:S[s][0] for s in sites if s in S}
for N in (0,150,400):
    row=[]
    for lo,hi in ((25,35),(35,40),(40,45),(45,50)):
        ss=[s for s in sites if lo<=lat.get(s,0)<hi]
        if ss:
            a=np.concatenate([P(s,N,'grain') for s in ss]); row.append(f"{lo}-{hi}N n={len(ss)}: bias {(a[:,1]-a[:,0]).mean():+.2f} MAE {np.abs(a[:,1]-a[:,0]).mean():.2f} (Cycles {a[:,0].mean():.1f})")
    print(f"grain N={N}: "+" | ".join(row))
# by Cycles site-mean yield tercile
for N in (0,150,400):
    cm={s:P(s,N,'grain')[:,0].mean() for s in sites}; q=np.percentile(list(cm.values()),[33,67]); row=[]
    for nm,sel in (("low",lambda x:x<q[0]),("mid",lambda x:q[0]<=x<q[1]),("high",lambda x:x>=q[1])):
        ss=[s for s in sites if sel(cm[s])]; a=np.concatenate([P(s,N,'grain') for s in ss]); row.append(f"{nm} n={len(ss)}: bias {(a[:,1]-a[:,0]).mean():+.2f} MAE {np.abs(a[:,1]-a[:,0]).mean():.2f} (Cycles {a[:,0].mean():.1f})")
    print(f"grain N={N} by site yield tercile: "+" | ".join(row))
