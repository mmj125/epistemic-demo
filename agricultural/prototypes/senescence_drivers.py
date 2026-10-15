"""What drives Cycles' canopy decline? (2026-10-15) Invert the paper's senescence sigmoid (c=-16, d=16 on a senescence clock) on Cycles' daily interception
after peak; implied clock rate vs thermal-time fraction, and vs Cycles' own state. Usage: python3 senescence_drivers.py"""
import sys,os,csv,datetime,numpy as np
sys.path.insert(0,'.');import swap_test as S
C0,D0,EIX,TTM=-16.0,16.0,0.99,1800.0
rows=[]
for site in S.ALL:
    for N in (0,150):
        prev=None
        for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
            if x['date'][0]=='#' or x['biomass']=='-999':prev=None;continue
            d=datetime.date.fromisoformat(x['date']);c=float(x['radiation_interception']);tt=float(x['thermal_time'])
            cur=(d.year,tt,c,1-float(x['nitrogen_stress'])/100,1-float(x['water_stress'])/100,float(x['aboveground_nitrogen_concentration']),site,N,float(x['grain_biomass']),float(x['aboveground_biomass']))
            if prev and prev[0]==cur[0] and tt>prev[1] and tt/TTM>0.5 and 0.1<c<0.9 and 0.1<prev[2]<0.9 and c<prev[2]:
                # senescence term: c = EIX/(1+exp(C0+D0*x)) given expansion term ~0 late
                xp=(np.log(EIX/prev[2]-1)-C0)/D0;xc=(np.log(EIX/c-1)-C0)/D0
                rows.append(((xc-xp)/((tt-prev[1])/TTM),prev[1]/TTM,cur[3],cur[4],cur[5],cur[9],cur[8],site,N,xc))
            prev=cur
r=np.array([x[0] for x in rows]);ok=(r>-1)&(r<6)
print('senescence days',ok.sum(),'rate r mean %.2f median %.2f'%(r[ok].mean(),np.median(r[ok])))
tt=np.array([x[1] for x in rows])[ok];Nm=np.array([x[2] for x in rows])[ok];W=np.array([x[3] for x in rows])[ok];conc=np.array([x[4] for x in rows])[ok];ag=np.array([x[5] for x in rows])[ok];gr=np.array([x[6] for x in rows])[ok];y=r[ok];Nn=np.array([x[8] for x in rows])[ok]
def binR2(x,y,nb=20):
    q=np.quantile(x,np.linspace(0,1,nb+1));idx=np.clip(np.searchsorted(q,x,side='right')-1,0,nb-1)
    m_=np.array([y[idx==i].mean() if (idx==i).any() else 0 for i in range(nb)]);return 1-((y-m_[idx])**2).sum()/((y-y.mean())**2).sum()
for nm,v in (('ttf',tt),('N mult',Nm),('W mult',W),('AG N conc',conc),('AG biomass',ag),('grain/AG',gr/np.maximum(ag,1e-6)),('N rate',Nn.astype(float))):
    print('  R2 of r on %-10s %.3f'%(nm,binR2(v,y)))
print('r by ttf bin (all), and for N=0 vs N=150')
for lo,hi in ((.5,.6),(.6,.7),(.7,.8),(.8,.9),(.9,1.0)):
    s=(tt>=lo)&(tt<hi)
    if s.sum()>50:print('  ttf %.1f-%.1f n=%5d r %.2f | N0 %.2f N150 %.2f'%(lo,hi,s.sum(),y[s].mean(),y[s&(Nn==0)].mean() if (s&(Nn==0)).any() else np.nan,y[s&(Nn==150)].mean() if (s&(Nn==150)).any() else np.nan))
