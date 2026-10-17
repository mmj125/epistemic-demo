"""Offline canopy-form test (2026-10-17): drive candidate canopy forms with Cycles' own thermal time and previous-day water/N stress multipliers and score daily rms against Cycles' interception, from emergence (thermal time >= 65) to the last day with data.
Forms: A closed-form two-clock sigmoid as in the engine (expansion on stress-weighted clock, senescence on thermal time); B integrated derivative (paper Eq. 6 text: state advanced by d(eps)/dTTf times the stress rate).
Usage: python3 corn_canopy_form_test_2026_10_17.py"""
import json,math,statistics as st
R=json.load(open("/tmp/w/canopy_daily_24.json"))
A_,B_,C_,D_=6,-20,-16,16; TM=1800.0
def f(xe,xs,eix): return eix/(1+math.exp(A_+B_*xe)+math.exp(C_+D_*xs))
def df(xe,xs,eix):  # derivative of the sigmoid wrt a common clock x (expansion and senescence both advance with x)
    e1=math.exp(A_+B_*xe); e2=math.exp(C_+D_*xs); den=(1+e1+e2)
    return eix*(-(B_*e1+D_*e2))/den**2
def run(sy,form,eix,pn,pw):
    L=sy["d"]; out=[]; xc=0.0; ei=f(0,0,eix); prev_tt=0.0; nprev=1.0; wprev=1.0
    for doy,tt,ci,w,n in L:
        dtt=max(0.0,tt-prev_tt); prev_tt=tt
        nf=nprev**pn if pn else 1.0; wf=wprev**pw if pw else 1.0
        if form=="A":
            xc+=dtt*nf*wf; ei=f(xc/TM,tt/TM,eix)
        elif form=="B":   # integrate derivative along thermal time, scaled by stress rate
            ei=max(0.0,min(eix,ei+df(tt/TM,tt/TM,eix)*(dtt/TM)*nf*wf))
        elif form=="C":   # expansion on stressed clock as A, but senescence term rate also N-reduced: clock for both
            xc+=dtt*nf*wf; ei=f(xc/TM,xc/TM,eix)
        if tt>=65: out.append((ei,ci))
        nprev=n; wprev=w
    return out
def score(form,eix,pn,pw,Nsel=None):
    se=0;k=0;per=[]
    for sy in R:
        if Nsel is not None and sy["N"]!=Nsel: continue
        o=run(sy,form,eix,pn,pw); s=sum((a-b)**2 for a,b in o); se+=s;k+=len(o)
    return (se/k)**.5
for label,Nsel in (("all",None),("N=0",0),("N=150",150)):
    print("==",label)
    for form,pn,pw in (("A",3.25,1.35),("A",0,0),("B",3.25,1.35),("B",3.25,0),("B",1,0),("B",2,0),("B",1,1.35),("B",0,0),("C",3.25,1.35),("C",3.25,0)):
        best=min(((score(form,e,pn,pw,Nsel),e) for e in (0.86,0.88,0.90,0.95,0.99)))
        print(f"form {form} pn {pn} pw {pw}: rms at eix .99 {score(form,0.99,pn,pw,Nsel):.4f}; best eix {best[1]} -> {best[0]:.4f}")
