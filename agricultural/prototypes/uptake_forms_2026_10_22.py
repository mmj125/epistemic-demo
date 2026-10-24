import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/up.npz')["A"]
site,N,year,doy,U,pn,ag,rt,st,tr=A[:,:10].T
def L(i,k): return A[:,10+7*i+k]
nl=4
conc_no3=[L(i,0) for i in range(nl)]; conc_nh4=[L(i,1) for i in range(nl)]; th=[L(i,2) for i in range(nl)]; thick=[L(i,3) for i in range(nl)]; bd=[L(i,4) for i in range(nl)]; fc=[L(i,5) for i in range(nl)]; pwp=[L(i,6) for i in range(nl)]
mass=[ (conc_no3[i]+conc_nh4[i])*bd[i]*thick[i]*10 for i in range(nl)]   # kg/ha mineral N in layer
pool=sum(mass); F=1-st/100
ok=(U>0)&(rt>0)&(ag>0.2)
print("days with uptake>0: %d ; by N factor: <0.6 %d, 0.6-0.9 %d, >0.9 %d"%(ok.sum(),(ok&(F<0.6)).sum(),(ok&(F>=0.6)&(F<0.9)).sum(),(ok&(F>=0.9)).sum()))
# 1. the cap view: U / pool on supply-limited days
sl=ok&(F<0.6)&(pool>0.5)
print("supply-limited days (F<0.6): n=%d, U mean %.3f kg/ha/day, pool mean %.1f, U/pool median %.3f mean %.3f (p10 %.3f p90 %.3f)"%(sl.sum(),U[sl].mean(),pool[sl].mean(),np.median(U[sl]/pool[sl]),(U[sl]/pool[sl]).mean(),*np.percentile(U[sl]/pool[sl],[10,90])))
odd=(site.astype(int)%2==1)
def r2(y,p,mk): return 1-((y-p)[mk]**2).sum()/((y[mk]-y[mk].mean())**2).sum()
def test(name,f,p0,xs):
    tr_=sl&odd; te=sl&~odd
    res=least_squares(lambda p:(f(p)-U)[tr_],p0,x_scale=xs); p=res.x; pr=f(p)
    # season totals per site-year on test sites (all alive days, not only supply-limited)
    print(f"  {name:44s} params {np.round(p,4)}  daily R2 train {r2(U,pr,tr_):.3f} test {r2(U,pr,te):.3f}")
    return p
print("supply-limited days, odd/even site hold-out")
# (a) cap: U = k * pool
test("a. cap  k*pool",lambda p:abs(p[0])*pool,[0.03],[0.01])
# (b) cap with root size: k*pool*rt/(rt+h)
test("b. k*pool*rt/(rt+h)",lambda p:abs(p[0])*pool*rt/(rt+abs(p[1])),[0.1,1.0],[0.05,0.5])
# (c) mass flow: transpiration (mm) x solution concentration (mg/L = mg/kg*bd/theta), weights by thickness in top 1 m
def massflow(p):
    s=0; z=0
    for i in range(nl):
        w=np.clip(1.0-z,0,thick[i])/np.maximum(thick[i],1e-6)  # share of layer within 1 m
        csol=(conc_no3[i]+conc_nh4[i])*bd[i]/np.maximum(th[i],0.02)   # mg/L
        s=s+w*thick[i]*csol; z=z+thick[i]
    return abs(p[0])*tr*s*0.01   # tr mm x mg/L = mg/m2 -> kg/ha x0.01 ; s sums csol*thick (m) ; scaled by k
test("c. mass flow  k*Tr*conc_solution",massflow,[0.1],[0.05])
# (d) Eq. 26 shape: sum_l RL_l * (1-exp(-a*(conc_l-xmin))) * SWF_l^2, RL ~ rt * exponential depth distribution
def eq26(p):
    k,a,xmin,h=abs(p[0]),abs(p[1]),abs(p[2]),abs(p[3]); s=0; z=0
    wts=[np.exp(-(z0)/max(h,0.05)) for z0 in np.cumsum([0]+[0.2]*nl)[:nl]]   # placeholder replaced below
    s=0; z=np.zeros(len(U))
    zs=[]
    tot=np.zeros(len(U)); parts=[]
    for i in range(nl):
        zmid=z+thick[i]/2; wl=np.exp(-zmid/max(h,0.05))*thick[i]; parts.append(wl); tot=tot+wl; z=z+thick[i]
    s=0
    for i in range(nl):
        conc=conc_no3[i]+conc_nh4[i]
        navail=1-np.exp(-a*np.maximum(conc-xmin,0))
        swf=np.clip((th[i]-pwp[i])/np.maximum(fc[i]-pwp[i],1e-6),0,1)
        s=s+(parts[i]/np.maximum(tot,1e-9))*navail*swf**2
    return k*rt*s
test("d. Eq.26: k*RL*(1-exp(-a(c-xmin)))*SWF^2",eq26,[0.05,0.2,0.2,0.3],[0.02,0.1,0.1,0.1])

print("== uptake against the demand of Cycles' actual growth: U vs dB(total retained) x 10 x marginal pct x scale")
import sys; sys.path.insert(0,'.')
import rhizo_engine as E, run_validation as rv
crop=dict(rv.CORN)
B=ag+rt
dB=np.zeros(len(B)); dB[1:]=B[1:]-B[:-1]
same=np.zeros(len(B),bool); same[1:]=(site[1:]==site[:-1])&(N[1:]==N[:-1])&(year[1:]==year[:-1])&(doy[1:]-doy[:-1]==1)
mdp=np.array([E.n_marginal_demand_pct(max(b,0.05),crop) for b in B])
dem=np.maximum(dB,0)*10*mdp
for lab,mk in (("F<0.6",ok&same&(F<0.6)),("0.6-0.9",ok&same&(F>=0.6)&(F<0.9)),("F>0.9",ok&same&(F>=0.9)),("all alive",ok&same)):
    x=dem[mk]; y=U[mk]; k=(x*y).sum()/(x*x).sum()
    print(f"  {lab:9s} n={mk.sum():6d} U mean {y.mean():.3f}, demand-of-actual-growth mean {x.mean():.3f}, best scale {k:.3f}, daily R2 at that scale {1-((y-k*x)**2).sum()/((y-y.mean())**2).sum():.3f}, corr {np.corrcoef(x,y)[0,1]:.3f}")
# and by N level the ratio of total season uptake to total demand
for n in (0,150):
    mk=ok&same&(N==n); print(f"  N={n}: sum U / sum demand = {U[mk].sum()/dem[mk].sum():.3f}")

print("== 7-day sums on supply-limited stretches (all 7 days F<0.6), pool = mean over the 7 days")
idx=np.where(same)[0]
wk=[]
i=0
n=len(U)
starts=[j for j in range(1,n-7) if all(same[j:j+7]) and (F[j:j+7]<0.6).all() and (U[j:j+7]>=0).all() and (rt[j:j+7]>0).all()]
# non-overlapping
sel=[];last=-10
for j in starts:
    if j>=last+7: sel.append(j); last=j
sel=np.array(sel); print("stretches:",len(sel))
Us=np.array([U[j:j+7].sum() for j in sel]); Ps=np.array([pool[j:j+7].mean() for j in sel]); Rt=np.array([rt[j:j+7].mean() for j in sel]); Ts=np.array([tr[j:j+7].sum() for j in sel]); S_=site[sel].astype(int)
Th=np.array([np.mean([ (th[0][j:j+7]-pwp[0][j:j+7])/np.maximum(fc[0][j:j+7]-pwp[0][j:j+7],1e-3)]) for j in sel])
Dm=np.array([dem[j:j+7].sum() for j in sel])
tr_=S_%2==1; te=~tr_
def fit1(name,x):
    k=(x[tr_]*Us[tr_]).sum()/(x[tr_]**2).sum(); p=k*x
    r=lambda mk:1-((Us-p)[mk]**2).sum()/((Us[mk]-Us[mk].mean())**2).sum()
    print(f"  {name:38s} k {k:.4f} weekly R2 train {r(tr_):.3f} test {r(te):.3f}")
fit1("a. k*pool*7",Ps*7)
fit1("b. k*pool*rt/(rt+0.74)*7",Ps*Rt/(Rt+0.74)*7)
fit1("e. k*pool*SWF(layer1)*7",Ps*Th*7)
fit1("f. k*Tr*pool",Ts*Ps)
fit1("g. k*demand of actual growth",Dm)
fit1("h. k*sqrt(pool*demand)",np.sqrt(Ps*Dm))

print("== concentration of new growth relative to the unstressed curve, against plant N status r = conc / critical (days with growth > 0.05 Mg/ha)")
agn_=pn*0.0
# above-ground N is not in the array; use total plant N status: total conc / critical at total biomass
crit=np.array([E.n_critical_pct(max(b,0.05), crop, crop.get("n_stress_crit_floor", E.N_STRESS_CRIT_FLOOR_MGHA)) for b in B])
rtot=(pn/(np.maximum(B,0.05)*10))/crit
g=ok&same&(dB>0.05)&(B>0.5)
cnew=U[g]/(dB[g]*10); q=cnew/(0.70*mdp[g]*1.0)   # relative to 0.70 x marginal curve
rr=rtot[g]
print("n=%d, corr(q, r) = %.3f"%(g.sum(),np.corrcoef(q,rr)[0,1]))
bins=[0,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.2]
for lo,hi in zip(bins[:-1],bins[1:]):
    k=(rr>=lo)&(rr<hi)
    if k.sum()>200: print(f"  r {lo:.1f}-{hi:.1f}: n {k.sum():6d} new-growth concentration / (0.70 x marginal curve): median {np.median(q[k]):.2f}  p25 {np.percentile(q[k],25):.2f} p75 {np.percentile(q[k],75):.2f}")
