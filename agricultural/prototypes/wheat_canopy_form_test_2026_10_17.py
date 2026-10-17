"""Offline wheat canopy form test (2026-10-17), as corn_canopy_form_test: closed-form two-clock sigmoid (engine) vs integrated derivative with only expansion slowed, driven by Cycles' own thermal time and previous-day water/N multipliers; daily rms against Cycles' interception, season-by-season. Usage: python3 wheat_canopy_form_test_2026_10_17.py"""
import json,math,statistics as st
R=json.load(open("/tmp/w/wheat_canopy_daily.json"))
A_,B_,C_,D_=6,-20,-16,16; TM=1800.0
def f(xe,xs,eix): return eix/(1+math.exp(A_+B_*xe)+math.exp(C_+D_*xs))
def parts(x,eix):
    e1=math.exp(A_+B_*x); e2=math.exp(C_+D_*x); den=(1+e1+e2)**2
    return eix*(-B_*e1)/den, eix*(-D_*e2)/den
def run(sy,form,eix,pn,pw,sn=0.0):
    out=[]; xc=0.0; prev=None; ei=None; nprev=wprev=1.0
    for doy,tt0,ci,w,n,tt in sy["d"]:
        if tt is None: continue
        if prev is None: prev=tt; ei=f(tt/TM,tt/TM,eix); xc=tt
        dtt=max(0.0,tt-prev); prev=tt
        nf=nprev**pn; wf=wprev**pw
        if form=="A":
            xc+=dtt*nf*wf; ei=f(xc/TM,tt/TM,eix)
        else:
            up,dn=parts(tt/TM,eix); ei=max(0.0,min(eix,ei+(up*nf*wf+dn*(nprev**sn))*dtt/TM))
        out.append((ei,ci)); nprev=n; wprev=w
    return out
def score(form,eix,pn,pw,Ns=None,sn=0.0):
    se=k=0
    for sy in R:
        if Ns is not None and sy["N"]!=Ns: continue
        o=run(sy,form,eix,pn,pw,sn); se+=sum((a-b)**2 for a,b in o); k+=len(o)
    return (se/k)**.5
for eix in (0.86,0.99):
    for lab,Ns in (("all",None),("N0",0),("N150",150)):
        print(f"eix {eix} {lab}: A(3.25,1.35) {score('A',eix,3.25,1.35,Ns):.4f}  A(3.17,1.35) {score('A',eix,3.17,1.35,Ns):.4f}  D(3.25,1.35) {score('D',eix,3.25,1.35,Ns):.4f}  D(3.17,1.35) {score('D',eix,3.17,1.35,Ns):.4f}  D(2,1) {score('D',eix,2,1,Ns):.4f}")
