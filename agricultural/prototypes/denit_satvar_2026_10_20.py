import os,sys,json
os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite as m_
from scipy.optimize import least_squares
S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)
fcs=[];pws=[];sts=[];cl=[];sa=[];so=[]
for s in SITES:
    lat,lon=S[s]; soil,_,_=m_.fd.resolve_field_soil(lat,lon); l=soil[0]
    sr=m_.saxton_rawls(l["sand"],l["clay"],l["soc"]*m_.OM_FROM_SOC); fcs.append(sr["fc"]);pws.append(sr["pwp"]);sts.append(sr["sat"]);cl.append(l["clay"]);sa.append(l["sand"]);so.append(l["soc"])
fcs,pws,sts,cl,sa,so=map(np.array,(fcs,pws,sts,cl,sa,so))
np.savez('/tmp/w/site_l1.npz',fc=fcs,pwp=pws,sat=sts,clay=cl,sand=sa,soc=so)
print("fc/sat range",np.round([ (f/s) for f,s in zip(fcs,sts)][:8],2))
A=np.load('/tmp/w/ndata.npz')['A']
prev=lambda a: np.concatenate([[0],a[:-1]])
same=np.zeros(len(A),bool); same[1:]=(A[1:,9]==A[:-1,9])&(A[1:,0]==A[:-1,0])&(A[1:,8]-A[:-1,8]==1)
def L(k,j): return A[:,14+10*k+j]
y=A[:,3]; resp=(A[:,12]+A[:,13])*1000; N=prev(L(0,2)); th=L(0,5); site=A[:,9].astype(int)
sub=same&(np.random.default_rng(2).random(len(A))<0.3)
FC=fcs[site]; PW=pws[site]; ST=sts[site]
def run(nm,s_):
    sp=prev(s_)
    f=lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*np.clip(sp,0,1.5)**abs(p[2])
    rr=least_squares(lambda p:(f(p)-y)[sub],[0.3,20,5],x_scale=[.1,2,1]); pp=f(rr.x)
    print(f"  {nm:34s} pooled R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(rr.x,3))
run("theta/sat",th/ST)
run("theta/fc",th/FC)
run("(theta-pwp)/(sat-pwp)",(th-PW)/(ST-PW))
run("(theta-fc)/(sat-fc) (clipped >=0)",np.clip((th-FC)/(ST-FC),0,None))
run("theta/(fc+0.5(sat-fc))",th/(FC+0.5*(ST-FC)))
run("theta only (m3/m3)",th)
print("sample site values (fc,pwp,sat):",[(round(a,3),round(b,3),round(c,3)) for a,b,c in zip(fcs[:5],pws[:5],sts[:5])])
def runa(nm,fs):
    f=lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*np.clip(prev(fs(p[3])),0,1.5)**abs(p[2])
    rr=least_squares(lambda p:(f(p)-y)[sub],[0.5,25,4.6,1.0],x_scale=[.1,2,1,.2],max_nfev=300); pp=f(rr.x)
    print(f"  {nm:40s} pooled R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(rr.x,3))
runa("(th - a pwp)/(sat - a pwp)",lambda a:(th-a*PW)/(ST-a*PW))
runa("(th - a*fc)/(sat - a*fc)",lambda a:(th-a*FC)/(ST-a*FC))
# per-site K spread with the better reference
sp=prev((th-PW)/(ST-PW)); out=[]
for i in range(24):
    ms=sub&(site==i)&(A[:,0]>=150)
    if ms.sum()<1500: continue
    f2=lambda p:abs(p[0])*resp*N/(N+28.0)*np.clip(sp,0,1.5)**4.64
    r2=least_squares(lambda p:(f2(p)-y)[ms],[0.7],x_scale=[.1]); out.append(abs(r2.x[0]))
print(" per-site K spread (n fixed 4.64): min %.2f med %.2f max %.2f  cv %.2f"%(min(out),np.median(out),max(out),np.std(out)/np.mean(out)))
print("== more references")
run("(th-pwp)/(fc-pwp)  plant-available fraction",(th-PW)/np.maximum(FC-PW,1e-3))
runa("(th - a pwp)/(sat - a pwp), free a",lambda a:(th-a*PW)/(ST-a*PW))
# two-parameter: theta0 = a*pwp, top = sat; with exponent also free already. Add Hill-type nitrate
def runb(nm,f,p0,xs):
    rr=least_squares(lambda p:(f(p)-y)[sub],p0,x_scale=xs,max_nfev=400); pp=f(rr.x)
    print(f"  {nm:40s} pooled R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(rr.x,3))
sa_=lambda a:np.clip(prev((th-a*PW)/(ST-a*PW)),0,1.5)
runb("a, resp^c",lambda p:abs(p[0])*np.maximum(resp,1e-6)**abs(p[4])*N/(N+abs(p[1]))*sa_(p[3])**abs(p[2]),[0.5,25,5,0.74,1.0],[.1,2,1,.1,.2])
runb("a, Hill nitrate",lambda p:abs(p[0])*resp*N**abs(p[4])/(N**abs(p[4])+abs(p[1])**abs(p[4]))*sa_(p[3])**abs(p[2]),[0.5,25,5,0.74,1.0],[.1,2,1,.1,.2])
runb("a, logistic sat",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))/(1+np.exp(np.clip(-(sa_(p[3])-p[2])/abs(p[4]),-50,50))),[0.5,25,0.8,0.74,0.1],[.1,2,.05,.1,.02])
print("== is the nitrification moisture cutoff the complement of the denitrification one?")
nh4=L(0,1); no3=L(0,0); T=L(0,7); y_n=A[:,1]
NHp=prev(nh4); NOp=prev(no3); rr_=NOp/np.maximum(NHp,1e-9)
def fT11(t): t=np.asarray(t,float); return np.where(t<=0,0.0,np.where(t<10,0.0105*t+0.00095*t*t,np.where(t<35,0.032*t-0.12,np.where(t<45,4.5-0.1*t,0.0))))
def nit(p,s_): return p[0]*fT11(T)*NHp/(1+(rr_/abs(p[1]))**abs(p[2]))/(1+np.exp(np.clip((s_-p[3])/abs(p[4]),-50,50)))
sn=(same&(np.random.default_rng(7).random(len(A))<0.25))
def fitn(nm,s_,p0=[0.206,8.2,6.2,0.795,0.078]):
    r=least_squares(lambda p:(nit(p,s_)-y_n)[sn],p0,x_scale=[.1,2,2,.05,.02],max_nfev=300); pp=nit(r.x,s_); print(f"  {nm:40s} R2 {1-((y_n-pp)[sn]**2).sum()/((y_n[sn]-y_n[sn].mean())**2).sum():.4f}",np.round(r.x,3))
fitn("raw theta/sat (today)",np.clip(th/ST,0,1.2))
for a in (0.5,0.74,1.0):
    fitn(f"(th-{a} pwp)/(sat-{a} pwp) (today)",np.clip((th-a*PW)/(ST-a*PW),0,1.5))
print("== denitrification saturation variable and shape (start-of-day)")
for a in (0.0,0.5,0.79,1.0):
    sa2=np.clip(prev((th-a*PW)/(ST-a*PW)),0,1.5)
    for nm,f,p0,xs in (("logistic",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))/(1+np.exp(np.clip(-(sa2-p[2])/abs(p[3]),-50,50))),[0.4,30,0.74,0.07],[.1,2,.05,.02]),
                       ("power",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*sa2**abs(p[2]),[0.6,30,5],[.1,2,1])):
        rr=least_squares(lambda p:(f(p)-y)[sub],p0,x_scale=xs,max_nfev=300); pp=f(rr.x)
        print(f"  a={a:<5} {nm:9s} R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(rr.x,3))
