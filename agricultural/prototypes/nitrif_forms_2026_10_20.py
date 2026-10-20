import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']
rng=np.random.default_rng(1); idx=rng.choice(len(A),250000,replace=False); A=A[idx]
y=A[:,1]
def L(k,j): return A[:,14+10*k+j]
no3=[L(k,0) for k in range(4)]; nh4=[L(k,1) for k in range(4)]; no3c=[L(k,2) for k in range(4)]; nh4c=[L(k,3) for k in range(4)]; cf=[L(k,4) for k in range(4)]; th=[L(k,5) for k in range(4)]; T=[L(k,7) for k in range(4)]; bd=[L(k,9) for k in range(4)]
print("mean nit",y.mean(),"nonzero",(y>1e-6).mean())
def R2(p): return 1-((y-p)**2).sum()/((y-y.mean())**2).sum()
def fit(name,fn,p0,xs=None):
    r=least_squares(lambda p:fn(p)-y,p0,x_scale=xs if xs is not None else 1.0,max_nfev=300); print(f" {name:60s} R2 {R2(fn(r.x)):.3f}  p {np.round(r.x,4)}"); return r.x
# current engine form on layer-1 (Cycles states)
def cur(p):
    r=no3[0]/np.maximum(nh4[0],1e-9); x=np.where(r<1e3,(r/8.982)**8.074,1e30); return nh4[0]*0.134/(1+np.exp(-0.246*(T[0]-13.355)))/(1+x)/(1+nh4[0]/568.5)
print(" current engine ratio form (layer 1, no refit)  R2",round(R2(cur(None)),3))
tot=sum(nh4)
fit("B  sum_i k cf_i^p NH4_i",lambda p:sum(p[0]*np.maximum(cf[i],0)**p[1]*nh4[i] for i in range(4)),[0.11,1.0])
fit("B1 layer1 only k cf^p NH4",lambda p:p[0]*np.maximum(cf[0],0)**p[1]*nh4[0],[0.11,1.0])
def sol(i): return nh4c[i]*bd[i]/np.maximum(th[i]+bd[i]*5.6,1e-3)   # mg per L-ish solution+sorbed partition
fit("C  sum k cf^p NH4 * 1/(1+K/Csol)",lambda p:sum(p[0]*np.maximum(cf[i],0)**p[1]*nh4[i]/(1+abs(p[2])/np.maximum(sol(i),1e-6)) for i in range(4)),[0.15,1.0,0.5],[.1,.1,.5])
fit("C2 sum k cf^p NH4 * conc/(conc+K) mg/kg",lambda p:sum(p[0]*np.maximum(cf[i],0)**p[1]*nh4[i]*nh4c[i]/(nh4c[i]+abs(p[2])) for i in range(4)),[0.15,1.0,0.5],[.1,.1,.5])
fit("D  sum k cf^p NH4/(1+(NO3/NH4/r0)^q)",lambda p:sum(p[0]*np.maximum(cf[i],0)**p[1]*nh4[i]/(1+(no3[i]/np.maximum(nh4[i],1e-9)/abs(p[2]))**abs(p[3])) for i in range(4)),[0.12,1.0,9,8],[.1,.1,2,2])
fit("E  sum k cf^p NH4 * sat-limited NH4 (1/(1+NH4c/K))",lambda p:sum(p[0]*np.maximum(cf[i],0)**p[1]*nh4[i]/(1+nh4c[i]/abs(p[2])) for i in range(4)),[0.15,1.0,50],[.1,.1,20])
fit("F  layer1 k cf^p NH4/(1+NH4c/K)",lambda p:p[0]*np.maximum(cf[0],0)**p[1]*nh4[0]/(1+nh4c[0]/abs(p[2])),[0.15,1.0,50],[.1,.1,20])
print("---- implied rate nit/NH4_layer1 binned by NH4 conc (rows) and NO3:NH4 ratio (cols)")
r1=no3[0]/np.maximum(nh4[0],1e-9); rate=y/np.maximum(nh4[0],1e-9)
m=(nh4[0]>0.05)&(cf[0]>0.3)&(cf[0]<0.6)
cb=[0,0.5,1,2,4,8,16,1e9]; rb=[0,1,3,6,9,12,20,50,1e9]
print("      ratio:"+"".join(f"{rb[j]:>7}-{rb[j+1] if rb[j+1]<1e8 else 'inf':<5}" for j in range(len(rb)-1)))
for i in range(len(cb)-1):
    row=[]
    for j in range(len(rb)-1):
        s=m&(nh4c[0]>=cb[i])&(nh4c[0]<cb[i+1])&(r1>=rb[j])&(r1<rb[j+1]); row.append(f"{rate[s].mean():.3f}({s.sum():>5})" if s.sum()>30 else "   -        ")
    print(f"NH4c {cb[i]:>4}-{cb[i+1] if cb[i+1]<1e8 else 'inf':<4}"+" ".join(row))
print("---- layer-1 forms")
def Tf(p,Tv): return 1/(1+np.exp(-p*(Tv-13.355)))
fit("H  k logistic(T) NH4/(1+(r/r0)^q)/(1+NH4/ks) [engine, refit]",lambda p:p[0]*Tf(p[1],T[0])*nh4[0]/(1+(r1/abs(p[2]))**abs(p[3]))/(1+nh4[0]/abs(p[4])),[0.134,0.246,8.98,8,568],[.1,.1,2,2,100])
fit("H2 k cf^p NH4/(1+(r/r0)^q)",lambda p:p[0]*np.maximum(cf[0],0)**p[1]*nh4[0]/(1+(r1/abs(p[2]))**abs(p[3])),[0.12,1,9,8],[.1,.1,2,2])
fit("G  min(k cf^p NH4, max(0,(R NH4 - NO3)/(1+R)))",lambda p:np.minimum(p[0]*np.maximum(cf[0],0)**p[1]*nh4[0],np.maximum(0,(abs(p[2])*nh4[0]-no3[0])/(1+abs(p[2])))),[0.12,1,10],[.1,.1,2])
fit("G2 k cf^p NH4 * clip((R-r)/R2,0,1)",lambda p:p[0]*np.maximum(cf[0],0)**p[1]*nh4[0]*np.clip((abs(p[2])-r1)/abs(p[3]),0,1),[0.12,1,12,6],[.1,.1,2,2])
# which T/moisture driver: cf vs logistic
fit("I  k cf^p NH4 / (1+exp((r-r0)/s))",lambda p:p[0]*np.maximum(cf[0],0)**p[1]*nh4[0]/(1+np.exp((r1-p[2])/abs(p[3]))),[0.12,1,8,1],[.1,.1,2,.5])
print("---- simplification")
fit("Hs engine form without ks",lambda p:p[0]*Tf(p[1],T[0])*nh4[0]/(1+(r1/abs(p[2]))**abs(p[3])),[0.134,0.246,8.98,8],[.1,.1,2,2])
fit("Gs cap form + logistic T, no ks",lambda p:np.minimum(p[0]*Tf(p[1],T[0])*nh4[0],np.maximum(0,(abs(p[2])*nh4[0]-no3[0])/(1+abs(p[2])))),[0.134,0.246,9.6],[.1,.1,2])
fit("Gs2 cap form + logistic T, softened (x^2 blend)",lambda p:p[0]*Tf(p[1],T[0])*nh4[0]*np.clip((abs(p[2])-r1)/abs(p[3])+1,0,1),[0.134,0.246,12,6],[.1,.1,2,2])
fit("Hs cubic-free: k logistic T NH4 / (1+(r/r0)^4)",lambda p:p[0]*Tf(p[1],T[0])*nh4[0]/(1+(r1/abs(p[2]))**4),[0.134,0.246,9],[.1,.1,2])
fit("Gk cap + logistic T + ks",lambda p:np.minimum(p[0]*Tf(p[1],T[0])*nh4[0]/(1+nh4[0]/abs(p[3])),np.maximum(0,(abs(p[2])*nh4[0]-no3[0])/(1+abs(p[2])))),[0.134,0.246,9.6,500],[.1,.1,2,100])
fit("Gk2 + free t0",lambda p:np.minimum(p[0]/(1+np.exp(-p[1]*(T[0]-p[4])))*nh4[0]/(1+nh4[0]/abs(p[3])),np.maximum(0,(abs(p[2])*nh4[0]-no3[0])/(1+abs(p[2])))),[0.134,0.246,9.6,500,13.3],[.1,.1,2,100,2])
print("---- Stockle and Campbell 1989 Eq 11 temperature (piecewise, normalised to 35 C) with ratio inhibition")
def fT11(Tv):
    Tv=np.asarray(Tv,float); return np.where(Tv<=0,0.0,np.where(Tv<10,0.0105*Tv+0.00095*Tv**2,np.where(Tv<35,0.032*Tv-0.12,np.where(Tv<45,4.5-0.1*Tv,0.0))))
fps=th[0]/L(0,6)
fit("S1 k fT11(T) NH4/(1+(r/r0)^q)/(1+NH4/ks)",lambda p:p[0]*fT11(T[0])*nh4[0]/(1+(r1/abs(p[1]))**abs(p[2]))/(1+nh4[0]/abs(p[3])),[0.2,9,8,500],[.1,2,2,100])
fit("S2 S1 * moisture (1-a fps)/(1+exp((fps-f0)/s))",lambda p:p[0]*fT11(T[0])*nh4[0]/(1+(r1/abs(p[1]))**abs(p[2]))/(1+nh4[0]/abs(p[3]))*np.clip(1-p[4]*fps,0,2)/(1+np.exp(np.clip((fps-p[5])/abs(p[6]),-50,50))),[0.2,9,8,500,0.3,0.8,0.08],[.1,2,2,100,.1,.05,.02])
fit("S3 logisticT version of S2",lambda p:p[0]*Tf(p[7],T[0])*nh4[0]/(1+(r1/abs(p[1]))**abs(p[2]))/(1+nh4[0]/abs(p[3]))*np.clip(1-p[4]*fps,0,2)/(1+np.exp(np.clip((fps-p[5])/abs(p[6]),-50,50))),[0.2,9,8,500,0.3,0.8,0.08,0.24],[.1,2,2,100,.1,.05,.02,.05])
fit("S4 S1 * logistic cutoff only",lambda p:p[0]*fT11(T[0])*nh4[0]/(1+(r1/abs(p[1]))**abs(p[2]))/(1+nh4[0]/abs(p[3]))/(1+np.exp(np.clip((fps-p[4])/abs(p[5]),-50,50))),[0.25,9,8,500,0.85,0.05],[.1,2,2,100,.05,.02])
fit("S5 S4 without ks",lambda p:p[0]*fT11(T[0])*nh4[0]/(1+(r1/abs(p[1]))**abs(p[2]))/(1+np.exp(np.clip((fps-p[3])/abs(p[4]),-50,50))),[0.25,9,8,0.85,0.05],[.1,2,2,.05,.02])
fit("S6 S4 with cap instead of ratio power",lambda p:np.minimum(p[0]*fT11(T[0])*nh4[0]/(1+nh4[0]/abs(p[1]))/(1+np.exp(np.clip((fps-p[3])/abs(p[4]),-50,50))),np.maximum(0,(abs(p[2])*nh4[0]-no3[0])/(1+abs(p[2])))),[0.25,500,9,0.85,0.05],[.1,100,2,.05,.02])
