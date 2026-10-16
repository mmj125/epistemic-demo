"""Soybean harvest-index law fitted from Cycles' own daily SoybeanMG.5 output (REFIT_PLAN row 53): HI = grain/aboveground at maturity against f_G, the share of aboveground
biomass made after the first reproductive day. Corn's law was fitted this way in row 6; soybean still carried placeholders (0.4 / 0.15 / 1.0)."""
import csv,glob,os,numpy as np
from scipy.optimize import least_squares
X=[]
for d in sorted(glob.glob('/tmp/cycles-run15/output/f*soyN0')):
    H={r['date'][:4]:r for r in csv.DictReader(open(d+'/harvest.csv')) if r['date'][0]!='#'}
    first={}
    for r in csv.DictReader(open(d+'/dailySoybeanMG.5.csv')):
        if r['date'][0]=='#' or r['stage']!='REPRODUCTIVE_GROWTH' or r['date'][:4] in first: continue
        first[r['date'][:4]]=float(r['aboveground_biomass'])
    for y,h in H.items():
        if y not in first: continue
        ag=float(h['total_biomass'])-float(h['root_biomass']);hi=float(h['harvest_index'])
        if ag>0.5: X.append((os.path.basename(d),int(y),(ag-first[y])/ag,hi,ag,0))
A=np.array([(x[2],x[3],x[4]) for x in X]);f,hi=A[:,0],A[:,1]
print('seasons',len(X),'HI mean %.3f sd %.3f, f_G mean %.3f'%(hi.mean(),hi.std(),f.mean()))
def res(p,f=f,hi=hi): return p[0]-(p[0]-p[1])*np.exp(-p[2]*f)-hi
r0=least_squares(res,[0.4,0.15,1.0]);r1=least_squares(res,[0.6,0.1,2.0])
for nm,r in(('placeholder start',r0),('alt start',r1)): print(nm,'Hx %.3f Ho %.3f k %.3f rms %.4f'%(*r.x,np.sqrt(np.mean(r.fun**2))))
print('placeholder (0.4,0.15,1.0) rms %.4f, mean pred %.3f'%(np.sqrt(np.mean(res([0.4,0.15,1.0])**2)),np.mean(hi+res([0.4,0.15,1.0]))))
b,a=np.polyfit(f,hi,1);print('linear HI = %.4f + %.4f f_G, rms %.4f, corr %.3f'%(a,b,np.sqrt(np.mean((a+b*f-hi)**2)),np.corrcoef(f,hi)[0,1]))
r2=least_squares(lambda p:p[0]-(p[0]-p[1])*np.exp(-p[2]*f)-hi,[0.4,0.3,3.0],bounds=([0.3,0.1,0.2],[0.5,0.38,20]))
print('bounded exp: Hx %.3f Ho %.3f k %.3f rms %.4f'%(*r2.x,np.sqrt(np.mean(r2.fun**2))))
for q in (0.1,0.5,0.9): print('f_G %.2f quantile -> HI mean %.3f'%(np.quantile(f,q),hi[(f>=np.quantile(f,q)-0.03)&(f<=np.quantile(f,q)+0.03)].mean()))
