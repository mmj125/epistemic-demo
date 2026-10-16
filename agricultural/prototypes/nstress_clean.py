"""Is Cycles' N stress a clean function of (aboveground N concentration / critical)? R2 of the ratio alone, then residual vs other variables (2026-10-15). Usage: python3 nstress_clean.py"""
import csv,glob,os,numpy as np,sys
sys.path.insert(0,'.');import cycles_engine_validate as E,run_validation_rotation2 as rv
crop=rv.CORN if hasattr(rv,'CORN') else None
if crop is None:
    import run_validation as r1;crop=r1.CORN
a,b=crop['n_max_conc']*100,crop['n_dilution_slope']
R=[]
for d in sorted(glob.glob('/tmp/cycles-run15/output/*N*')):
    site=os.path.basename(d)
    if not site.endswith(('N0','N150','N400')) or site.startswith(('h2h','iowaX')):continue
    prev=None
    for x in csv.DictReader(open(d+'/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999' or x['crop']=='-':continue
        ag=float(x['aboveground_biomass']);c=float(x['aboveground_nitrogen_concentration'])/10.0
        if ag<1.0:continue
        r=c/(a*ag**(-b)) ;s=float(x['nitrogen_stress'])/100;tt=float(x['thermal_time'])
        R.append((r,s,tt,float(x['water_stress'])/100,float(x['o2_factor']) if x['o2_factor'] not in('','-') else 0,ag,hash(site.rstrip('0123456789N')) %1000))
R=np.array(R);print('n days',len(R))
r,s=R[:,0],R[:,1]
bins=np.linspace(0.2,1.2,21)
print('ratio bin   n   mean stress  sd')
for lo,hi in zip(bins[:-1],bins[1:]):
    m=(r>=lo)&(r<hi)
    if m.sum()>50:print(' %.2f-%.2f %6d  %.3f  %.3f'%(lo,hi,m.sum(),s[m].mean(),s[m].std()))
# binned-mean predictor R2
idx=np.digitize(r,np.linspace(0.1,1.5,57));pred=np.array([s[idx==i].mean() for i in idx]) if False else None
mu={i:s[idx==i].mean() for i in set(idx)};pred=np.array([mu[i] for i in idx])
print('R2 of stress on ratio alone (binned): %.3f'%(1-((s-pred)**2).sum()/((s-s.mean())**2).sum()))
res=s-pred
for nm,col in (('thermal_time',2),('water_stress',3),('o2',4),('AG biomass',5)):
    print('corr(residual, %s) %.3f'%(nm,np.corrcoef(res,R[:,col])[0,1]))
