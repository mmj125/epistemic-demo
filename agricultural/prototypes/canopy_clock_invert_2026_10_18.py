"""Invert Cycles' daily canopy cover on the expansion sigmoid eix/(1+exp(6-20x)) to get the implied clock x, then its daily rate ratio r = dx*TM/dTT against the thermal-time increment, binned by previous-day N and water stress multipliers and by stage. If the paper's law (rate reduced by N stress) held with a unit clock, r would equal 1 unstressed. Usage: python3 canopy_clock_invert_2026_10_18.py [corn|wheat]"""
import json,math,sys
import numpy as np
crop=sys.argv[1] if len(sys.argv)>1 else "corn"
R=json.load(open("/tmp/w/canopy_daily_24.json" if crop=="corn" else "/tmp/w/wheat_canopy_daily.json"))
TM=1800.0; eix=0.99 if crop=="corn" else 0.86
rows=[]
for sy in R:
    L=sy["d"]; prev=None
    for rec in L:
        doy,tt,ci,w,n=rec[:5]
        if prev is not None and 0.03<ci<0.9*eix and 0.03<prev[2]<0.9*eix and tt<0.8*TM:
            x=(6-math.log(eix/ci-1))/20; xp=(6-math.log(eix/prev[2]-1))/20; dtt=tt-prev[1]
            if dtt>5: rows.append((tt/TM,(x-xp)*TM/dtt,prev[3],prev[4],ci,sy["N"]))
        prev=rec[:5]
A=np.array(rows,dtype=float); print(crop,"expansion-phase days",len(A),"median r (all)",round(float(np.median(A[:,1])),3))
print("r by previous-day N multiplier (water>=0.97):")
for lo,hi in ((0,.3),(.3,.6),(.6,.8),(.8,.9),(.9,.97),(.97,1.01)):
    k=(A[:,3]>=lo)&(A[:,3]<hi)&(A[:,2]>=.97); print(f"  N {lo}-{hi}: median r {np.median(A[k,1]):.2f} mean {A[k,1].mean():.2f} (n {k.sum()})") if k.sum()>30 else None
print("r by previous-day water multiplier (N>=0.97):")
for lo,hi in ((0,.3),(.3,.6),(.6,.8),(.8,.9),(.9,.97),(.97,1.01)):
    k=(A[:,2]>=lo)&(A[:,2]<hi)&(A[:,3]>=.97); print(f"  W {lo}-{hi}: median r {np.median(A[k,1]):.2f} mean {A[k,1].mean():.2f} (n {k.sum()})") if k.sum()>30 else None
print("r by thermal-time fraction (unstressed):")
for lo,hi in ((0,.1),(.1,.15),(.15,.2),(.2,.25),(.25,.3),(.3,.4),(.4,.6),(.6,.8)):
    k=(A[:,0]>=lo)&(A[:,0]<hi)&(A[:,2]>=.97)&(A[:,3]>=.97); print(f"  ttf {lo}-{hi}: median r {np.median(A[k,1]):.2f} (n {k.sum()})") if k.sum()>30 else None
