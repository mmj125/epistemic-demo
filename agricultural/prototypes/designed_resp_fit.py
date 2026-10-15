"""Fit Cycles' per-layer SOM respiration law from the designed fallow runs (REFIT_PLAN row 42): k_eff = annual respired C / sum_days(fE * Cs) per layer versus depth and saturation ratio Cs/Csx(clay)."""
import csv,json,glob,math,numpy as np,sys
sys.path.insert(0,'.')
import designed_fallow as D
CY=D.CY;rows=[]
for T in D.TEMPS:
 for rain in D.RAINS:
  for soc0 in D.SOCS:
   for clay in D.CLAYS:
    tag=f"df_{T}_{int(rain*10)}_{int(soc0*10)}_{clay}";d=f"{CY}/output/{tag}"
    try:
        L=list(csv.reader(open(f"{d}/dailySoilLayersCN.csv")));P=list(csv.reader(open(f"{d}/annualSoilProfileC.csv")))
    except Exception:continue
    h=L[0];cf=[h.index(f"composite_factor.{i}") for i in range(1,len(D.TH)+1)];sc=[h.index(f"soil_organic_carbon.{i}") for i in range(1,len(D.TH)+1)]
    hp=P[0];rs=[hp.index(f"respired_carbon.{i}") for i in range(1,len(D.TH)+1)]
    if rs is None:print(hp);sys.exit()
    sraw=D.soil_raw(soc0,clay);z=0;zs=[]
    for l in sraw:zs.append(z+l['thick']/2);z+=l['thick']
    byyr={}
    for r in L[2:]:byyr.setdefault(int(r[0][:4]),[]).append(r)
    for r in P[2:]:
        y=int(r[0])
        if y<2001+D.SPIN or y not in byyr:continue
        for i in range(len(D.TH)):
            S=sum(float(q[cf[i]])*float(q[sc[i]]) for q in byyr[y]);R=float(r[rs[i]])
            if R<=0 or S<=0:continue
            cs=np.mean([float(q[sc[i]]) for q in byyr[y]])
            thick=sraw[i]['thick'];soc_pct=sraw[i]['soc'];csx=2.11+3.75*clay/100
            rows.append((T,rain,soc0,clay,i,zs[i],soc_pct/csx,R/S,np.mean([float(q[cf[i]]) for q in byyr[y]])))
A=np.array(rows);print(len(A))
np.save('/tmp/w/resp_rows.npy',A)
z=A[:,5];ratio=A[:,6];k=np.log(A[:,7])
X=np.column_stack([np.ones(len(A)),z,np.log(ratio)]);b=np.linalg.lstsq(X,k,rcond=None)[0];r=k-X@b
print('log k = %.3f + %.3f z + %.3f ln(ratio)  rms %.3f'%(b[0],b[1],b[2],r.std()))
# ratio dependence by bins
for lo,hi in [(0,0.1),(0.1,0.2),(0.2,0.35),(0.35,0.5),(0.5,0.7),(0.7,1.0),(1.0,5)]:
    m=(ratio>=lo)&(ratio<hi)
    if m.sum()>5:print('ratio %.2f-%.2f n %d  median k*exp(%.2f z): %.3e'%(lo,hi,m.sum(),-b[1],np.median(np.exp(k[m]-b[1]*z[m]))))
