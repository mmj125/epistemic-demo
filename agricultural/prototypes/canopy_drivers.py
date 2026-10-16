"""What drives Cycles' canopy expansion? (2026-10-15) Invert the paper's expansion sigmoid on Cycles' daily radiation_interception to get the implied clock
rate r = d(clock)/d(thermal-time fraction) in the expansion phase, then see which of Cycles' own daily variables explain r. Usage: python3 canopy_drivers.py"""
import sys,os,csv,datetime,json,numpy as np
sys.path.insert(0,'.');import swap_test as S
A,B,EIX,TTM=6.0,-20.0,0.99,1800.0
rows=[]
for site in S.ALL:
    for N in (0,150):
        prev=None
        for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
            if x['date'][0]=='#' or x['biomass']=='-999':prev=None;continue
            d=datetime.date.fromisoformat(x['date']);c=float(x['radiation_interception']);tt=float(x['thermal_time'])
            cur=(d.year,tt,c,1-float(x['nitrogen_stress'])/100,1-float(x['water_stress'])/100,float(x['temperature_factor']),float(x['o2_factor']),float(x['aboveground_nitrogen_concentration']),float(x['biomass']),site,N)
            if prev and prev[0]==cur[0] and 0.08<prev[2]<0.8 and 0.08<c<0.8 and tt>prev[1] and tt/TTM<0.55:
                xp=(A-np.log(EIX/prev[2]-1))/(-B)*-1 if False else (np.log(EIX/prev[2]-1)-A)/B
                xc=(np.log(EIX/c-1)-A)/B
                dx=xc-xp;dtt=(tt-prev[1])/TTM
                rows.append((dx/dtt,prev[3],prev[4],cur[3],cur[4],cur[5],cur[6],cur[7],cur[8],tt/TTM,site,N))
            prev=cur
print('expansion-phase days',len(rows))
R=np.array([[r[0]]+list(r[1:10]) for r in rows],float);r=R[:,0]
print('implied clock rate r: mean %.2f median %.2f p10 %.2f p90 %.2f'%(r.mean(),np.median(r),np.percentile(r,10),np.percentile(r,90)))
names=['N mult (prev day)','W mult (prev day)','N mult','W mult','temperature_factor','o2_factor','AG N conc','biomass','ttf']
ok=(r>0)&(r<5)
for i,n in enumerate(names):
    print('  corr(r, %-18s) %+.2f'%(n,np.corrcoef(r[ok],R[ok,i+1])[0,1]))
def fit(cols,logs=True):
    y=np.log(r[ok]);X=np.c_[np.ones(ok.sum()),np.log(np.maximum(R[ok][:,cols],1e-3))];b=np.linalg.lstsq(X,y,rcond=None)[0]
    res=y-X@b;return b,1-res.var()/y.var()
for nm,cols in (('N prev',[1]),('W prev',[2]),('N prev, W prev',[1,2]),('N prev, W prev, tempfactor',[1,2,5]),('N prev, W prev, o2',[1,2,6]),('N,W prev + AG N conc',[1,2,7])):
    b,r2=fit(cols);print('  log r ~ %-30s R2 %.3f  coef %s'%(nm,r2,np.round(b,2)))
print('binned: r by N mult prev day (W>0.9)')
for lo,hi in ((0,.3),(.3,.5),(.5,.7),(.7,.9),(.9,.99),(.99,1.01)):
    s=ok&(R[:,1]>=lo)&(R[:,1]<hi)&(R[:,2]>.9)
    if s.sum()>30:print('   N %.2f-%.2f n=%6d r mean %.2f'%(lo,hi,s.sum(),r[s].mean()))
print('binned: r by W mult prev day (N>0.97)')
for lo,hi in ((0,.3),(.3,.6),(.6,.8),(.8,.9),(.9,.97),(.97,1.01)):
    s=ok&(R[:,2]>=lo)&(R[:,2]<hi)&(R[:,1]>.97)
    if s.sum()>30:print('   W %.2f-%.2f n=%6d r mean %.2f'%(lo,hi,s.sum(),r[s].mean()))
json.dump([list(map(lambda v:v if isinstance(v,str) else float(v),x)) for x in rows[:200000]],open('/tmp/w/canopy_rate.json','w'))
