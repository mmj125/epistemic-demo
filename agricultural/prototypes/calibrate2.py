"""Second simultaneous calibration (2026-10-14): ~24 parameters, objective includes the nitrogen-loss pathways, held-out gate.
Coordinate descent in log space on the 16 TUNING sites, N = 0/150/400, continuous chain. The 12 held-out sites are scored at the start,
every 8 accepted moves, and at the end. Usage: python3 calibrate2.py [max_evals] [resume]  -> /tmp/w/cal2_*.json"""
import sys,os,csv,json,time,random,math,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
import cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
TUNE=list(m.SITES);HELD=list(m.HELDOUT_SITES)
# name: (lo, hi, rel_step). Multiplicative parameters move in log space within [lo,hi] times the starting value; absolute ones within [lo,hi].
REL={'SIXPOOL_ML_N_A':(0.55,1.5,0.10),'SIXPOOL_ML_N_B':(0.5,1.8,0.12),'SIXPOOL_ML_N_C':(0.4,2.0,0.2),'SIXPOOL_ML_KS':(0.6,1.4,0.08),'SIXPOOL_ML_FD_R0':(0.7,1.6,0.08),
 'SIXPOOL_N_POT_MULT':(0.65,1.4,0.08),'SIXPOOL_N_HALF_MGKG':(0.5,2.0,0.2),'N_DEMAND_SCALE':(0.7,1.2,0.05),'ROOT_DENSITY_DECAY_M':(0.5,2.0,0.15),
 'SOIL_EVAP_SCALE':(0.75,1.3,0.06),'RESIDUE_COVER_K':(0.6,1.6,0.12),'N2O_NITRIF_FRAC':(0.5,3.0,0.25),'N2O_DENIT_A':(0.5,3.0,0.25),
 'VOLATILIZATION_RATE_A':(0.4,2.5,0.2),'DENITRIF_THR_K':(0.3,3.0,0.25),'CANOPY_N_POW':(0.5,1.6,0.1),'CANOPY_WATER_POW':(0.6,1.5,0.1),'GRAIN_MULT':(0.9,1.2,0.025)}
ABS={'CANOPY_C':(-18.0,-8.0,1.5),'CANOPY_D':(8.0,20.0,1.5),'CANOPY_EIX':(0.9,1.0,0.015),'N_STRESS_ZERO_RATIO':(0.5,1.0,0.06),'N_STRESS_KNEE_RATIO':(0.26,0.5,0.04)}
def start_params():
    p={k:float(getattr(E,k)) for k in REL if k!='GRAIN_MULT'};p['GRAIN_MULT']=1.0
    p['CANOPY_C'],p['CANOPY_D']=E.CANOPY_SHAPE_FORCE[2],E.CANOPY_SHAPE_FORCE[3];p['CANOPY_EIX']=E.CANOPY_EIX_FORCE
    p['N_STRESS_ZERO_RATIO']=E.N_STRESS_ZERO_RATIO;p['N_STRESS_KNEE_RATIO']=E.N_STRESS_KNEE_RATIO
    return p
P0=start_params()
def apply(p):
    for k in REL:
        if k=='GRAIN_MULT':os.environ['GRAIN_MULT']=str(p[k])
        else:setattr(E,k,p[k])
    E.CANOPY_SHAPE_FORCE=(6,-20,p['CANOPY_C'],p['CANOPY_D']);E.CANOPY_EIX_FORCE=p['CANOPY_EIX']
    E.N_STRESS_ZERO_RATIO=p['N_STRESS_ZERO_RATIO'];E.N_STRESS_KNEE_RATIO=p['N_STRESS_KNEE_RATIO']
def bounds(k):
    if k in REL:lo,hi,_=REL[k];return lo*P0[k],hi*P0[k]
    lo,hi,_=ABS[k];return lo,hi
def step0(k):return REL[k][2] if k in REL else ABS[k][2]
def job(a):
    site,N,p=a;apply(p)
    lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    try:r=m.engine(site,wx,soil,cl,N,'leadin')
    except Exception:return None
    H,A=m.run_cycles(site,N);ys=[y for y in r if y in H and y in A]
    g=np.array([H[y]['grain'] for y in ys]);e=np.array([r[y]['grain'] for y in ys])
    c=float(np.corrcoef(g,e)[0,1]) if g.std()>1e-9 and e.std()>1e-9 else 0.0
    mean=lambda k,ek:(float(np.mean([A[y][k] for y in ys])),float(np.mean([r[y].get(ek,0.0) for y in ys])))
    return dict(site=site,N=N,mae=float(np.abs(g-e).mean()),bias=float((e-g).mean()),corr=c,em=float(e.mean()),cm=float(g.mean()),
                leach=mean('leach','n_leached_kg_ha'),denit=mean('denit','n_denitrified_kg_ha'),volat=mean('volat','n_volatilized_pool_kg_ha'),n2o=mean('n2o','n2o_emitted_kg_ha'))
def objective(pool,p,sites):
    res=[r for r in pool.map(job,[(s,N,p) for s in sites for N in (0,150,400)]) if r]
    if len(res)<len(sites)*3:return 99.0,{}
    by={N:sorted([r for r in res if r['N']==N],key=lambda r:r['site']) for N in (0,150,400)}
    mae={N:np.mean([r['mae'] for r in by[N]]) for N in by};cor={N:np.mean([r['corr'] for r in by[N]]) for N in by}
    em={N:np.array([r['em'] for r in by[N]]) for N in by};cm={N:np.array([r['cm'] for r in by[N]]) for N in by}
    r1=abs((em[150]-em[0]).mean()-(cm[150]-cm[0]).mean())/1.5;r2=abs((em[400]-em[150]).mean()-(cm[400]-cm[150]).mean())/2.5
    def rms(key,N):
        l=[math.log((r[key][1]+.1)/(r[key][0]+.1)) for r in by[N]];return math.sqrt(np.mean(np.square(l)))
    loss=np.mean([rms('leach',150),rms('leach',400),rms('denit',150),rms('denit',400),rms('volat',150),rms('n2o',150),rms('n2o',400)])
    J=mae[0]+mae[150]+mae[400]+(1-cor[150])+0.5*(1-cor[0])+0.5*(1-cor[400])+0.5*(r1+r2)+0.5*loss
    return J,dict(mae={int(N):float(v) for N,v in mae.items()},corr={int(N):float(v) for N,v in cor.items()},loss=float(loss),resp=(float(r1),float(r2)))
if __name__=="__main__":
    budget=int(sys.argv[1]) if len(sys.argv)>1 else 100
    pool=Pool(4);t0=time.time()
    p=dict(P0)
    if len(sys.argv)>2 and sys.argv[2]=='resume':p=json.load(open('/tmp/w/cal2_best.json'))['p']
    base_t,bd=objective(pool,P0,TUNE);base_h,bh=objective(pool,P0,HELD)
    print('BASELINE tuning J %.4f held J %.4f'%(base_t,base_h),bd,bh,flush=True)
    best,detail=objective(pool,p,TUNE);n=1;accepts=0
    step={k:step0(k) for k in p};log=[]
    keys=list(p)
    while n<budget and max(step[k]/step0(k) for k in step)>0.2:
        improved=False;random.shuffle(keys)
        for k in keys:
            if n>=budget:break
            for sgn in (+1,-1):
                lo,hi=bounds(k)
                q=dict(p);q[k]=p[k]*math.exp(sgn*step[k]) if k in REL else p[k]+sgn*step[k]
                q[k]=min(hi,max(lo,q[k]))
                if q[k]==p[k]:continue
                J,dt=objective(pool,q,TUNE);n+=1
                print('eval %3d %-24s -> %.5g  J %.4f (best %.4f) %.0fs'%(n,k,q[k],J,best,time.time()-t0),flush=True)
                if J<best-1e-4:
                    best,p,detail=J,q,dt;improved=True;accepts+=1;log.append((n,best,k))
                    json.dump(dict(best=best,p=p,log=log),open('/tmp/w/cal2_best.json','w'))
                    if accepts%8==0:
                        hj,hd=objective(pool,p,HELD);print('   HELD-OUT check at accept %d: J %.4f (baseline %.4f)'%(accepts,hj,base_h),hd,flush=True)
                    break
        if not improved:
            for k in step:step[k]*=0.5
            print('no improvement in a pass; halving steps',flush=True)
    hj,hd=objective(pool,p,HELD)
    json.dump(dict(baseline_tune=base_t,baseline_held=base_h,baseline_tune_detail=bd,baseline_held_detail=bh,best_tune=best,best_held=hj,p=p,P0=P0,tune_detail=detail,held_detail=hd,evals=n),open('/tmp/w/cal2_final.json','w'),default=float,indent=1)
    print('FINAL tuning J %.4f (baseline %.4f)  held-out J %.4f (baseline %.4f)'%(best,base_t,hj,base_h))
    print({k:(round(P0[k],5),round(p[k],5)) for k in p if abs(p[k]-P0[k])>1e-12})
    print('tuning',detail,'| baseline',bd);print('held  ',hd,'| baseline',bh)
