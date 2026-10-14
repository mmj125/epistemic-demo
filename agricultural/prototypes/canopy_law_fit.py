import sys,os,csv,numpy as np
sys.path.insert(0,'.')
import cycles_engine_validate as E, run_validation_multisite as m
sites=list(m.SITES)+list(m.HELDOUT_SITES)
TTM=1800.0;shape=E.DEFAULT_CANOPY_SHAPE
xs=np.linspace(0,0.6,6001);cc=np.array([E.canopy_cover(x,1.0,shape) for x in xs]);cc_inc=np.maximum.accumulate(cc)
def inv(I): return float(np.interp(I,cc_inc,xs))
P=[]
for s in sites:
    for N in (0,150):
        prev=None
        for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{s}N{N}/dailyCornRM.90.csv')):
            if x['date'][0]=='#' or x['biomass']=='-999':prev=None;continue
            I=float(x['radiation_interception']);TT=float(x['thermal_time']);ws=1-float(x['water_stress'])/100;ns=1-float(x['nitrogen_stress'])/100
            if prev is not None:
                I0,TT0,ws0,ns0,d0=prev
                dtt=TT-TT0
                if dtt>3 and 0.04<I0<0.8 and 0.04<I<0.85 and I>=I0 and x['date'][:4]==d0[:4]:
                    rate=(inv(I)-inv(I0))*TTM/dtt
                    P.append((s,N,rate,ws0,ns0,I0))
            prev=(I,TT,ws,ns,x['date'])
a=np.array([(p[2],p[3],p[4],p[5]) for p in P]);print('pairs',len(a))
rate,ws,ns,I0=a.T
print('rate quantiles',np.percentile(rate,[5,25,50,75,95]).round(2))
# bin
def tab(lo,hi,name):
    sel=(ws>=lo[0])&(ws<hi[0])&(ns>=lo[1])&(ns<hi[1]);return sel.sum(),np.median(rate[sel]) if sel.sum()>30 else float('nan')
print('median canopy-clock rate (1 = unstressed) by water mult (rows) and N mult (cols)')
wb=[(0,.3),(.3,.6),(.6,.9),(.9,1.01)];nb=[(0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,.95),(.95,1.01)]
print('        '+'  '.join('N%.2f-%.2f'%b for b in nb))
for w in wb:
    print('W%.1f-%.2f '%w+'  '.join('%5.2f(%5d)'%tuple(reversed(tab((w[0],n[0]),(w[1],n[1]),''))) if False else '%5.2f(%4d)'%(tab((w[0],n[0]),(w[1],n[1]),'')[1],tab((w[0],n[0]),(w[1],n[1]),'')[0]) for n in nb))
# fit forms on unstressed-normalized rate: base rate from ws>.95 & ns>.95
base=np.median(rate[(ws>.95)&(ns>.95)]);print('base rate',round(base,3))
r=rate/base
from scipy.optimize import least_squares
def fit(f,p0):
    res=least_squares(lambda p:f(p,ws,ns)-r,p0);return res.x,np.sqrt(np.mean(res.fun**2))
print('power ws^a*ns^b',*fit(lambda p,w,n:w**p[0]*n**p[1],[1,1]))
print('ws^a*(1-c(1-ns))',*fit(lambda p,w,n:w**p[0]*(1-p[1]*(1-n)),[1,.5]))
print('ws^a*ns^b with scale',*fit(lambda p,w,n:p[2]*w**p[0]*n**p[1],[1,1,1]))
print('min(ws,ns)^a',*fit(lambda p,w,n:np.minimum(w,n)**p[0],[1]))
