"""Simultaneous calibration (2026-10-14) of the parameters of the modules the module-swap test identified (canopy, N stress,
N supply, grain factor), by coordinate descent on a composite objective over the 16 TUNING sites; the 12 held-out sites are
evaluated only at the end (and every improvement is logged). Usage: python3 calibrate.py [max_evals]. Writes /tmp/w/calib_*.json"""
import sys,os,csv,json,time,random,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
import cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
TUNE=list(m.SITES);HELD=list(m.HELDOUT_SITES)
SPEC={ # name: (start, lo, hi, step)
 'gm':(1.05,0.9,1.2,0.03),'npow':(3.85,1.0,5.0,0.6),'wpow':(1.35,0.8,2.0,0.2),'c':(-16.0,-18.0,-8.0,1.5),'d':(16.0,8.0,20.0,2.0),
 'eix':(0.95,0.88,1.0,0.02),'zr':(0.70,0.50,0.95,0.08),'knee':(0.30,0.26,0.50,0.05),'nds':(0.75,0.50,1.00,0.08),'A':(66.0,50.0,85.0,6.0)}
def apply(p):
    E.CANOPY_TWO_CLOCK=True;E.CANOPY_N_POW=p['npow'];E.CANOPY_WATER_POW=p['wpow'];E.CANOPY_SHAPE_FORCE=(6,-20,p['c'],p['d']);E.CANOPY_EIX_FORCE=p['eix']
    E.N_STRESS_ZERO_RATIO=p['zr'];E.N_STRESS_KNEE_RATIO=p['knee'];E.N_DEMAND_SCALE=p['nds'];E.SIXPOOL_ML_N_A=p['A'];os.environ['GRAIN_MULT']=str(p['gm'])
def reset_defaults():
    E.CANOPY_TWO_CLOCK=False;E.CANOPY_N_POW=None;E.CANOPY_WATER_POW=1.0;E.CANOPY_SHAPE_FORCE=None;E.CANOPY_EIX_FORCE=None
    E.N_STRESS_ZERO_RATIO=0.7;E.N_STRESS_KNEE_RATIO=0.3;E.N_DEMAND_SCALE=0.75;E.SIXPOOL_ML_N_A=61.0;os.environ.pop('GRAIN_MULT',None)
_ref={}
def ref(site,N):
    k=(site,N)
    if k not in _ref:
        d=f'/tmp/cycles-run15/output/{site}N{N}'
        H={int(x['date'][:4]):float(x['grain_yield']) for x in csv.DictReader(open(d+'/harvest.csv')) if x['date'][0]!='#'}
        A={int(x['year']):float(x['NO3_leaching'])+float(x['NH4_leaching']) for x in csv.DictReader(open(d+'/annualN.csv')) if x['year'][0]!='#'}
        _ref[k]=(H,A)
    return _ref[k]
def job(a):
    site,N,p=a
    if p is None: reset_defaults()
    else: apply(p)
    lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    try:
        r=m.engine(site,wx,soil,cl,N,'leadin')
    except Exception:
        return dict(site=site,N=N,mae=9.0,bias=0.0,corr=0.0,em=0.0,cm=1.0,le=0.0,lc=0.0)
    H,A=ref(site,N)
    ys=[y for y in r if y in H and y in A]
    g=np.array([H[y] for y in ys]);e=np.array([r[y]['grain'] for y in ys])
    c=float(np.corrcoef(g,e)[0,1]) if g.std()>1e-9 and e.std()>1e-9 else 0.0
    return dict(site=site,N=N,mae=float(np.abs(g-e).mean()),bias=float((e-g).mean()),corr=c,em=float(e.mean()),cm=float(g.mean()),
                le=float(np.mean([r[y].get('n_leached_kg_ha',0.0) for y in ys])),lc=float(np.mean([A[y] for y in ys])))
def objective(pool,p,sites):
    res=pool.map(job,[(s,N,p) for s in sites for N in (0,150,400)])
    by={N:[r for r in res if r['N']==N] for N in (0,150,400)}
    mae={N:np.mean([r['mae'] for r in by[N]]) for N in by};cor={N:np.mean([r['corr'] for r in by[N]]) for N in by}
    resp_e=np.mean([(r2['em']-r0['em']) for r0,r2 in zip(sorted(by[0],key=lambda r:r['site']),sorted(by[150],key=lambda r:r['site']))])/1.5
    resp_c=np.mean([(r2['cm']-r0['cm']) for r0,r2 in zip(sorted(by[0],key=lambda r:r['site']),sorted(by[150],key=lambda r:r['site']))])/1.5
    leach=np.mean([abs(r['le']-r['lc']) for N in (150,400) for r in by[N]])
    J=mae[0]+mae[150]+mae[400]+1.0*(1-cor[150])+0.5*(1-cor[0])+0.5*(1-cor[400])+0.5*abs(resp_e-resp_c)+leach/100.0
    bias={N:np.mean([r['bias'] for r in by[N]]) for N in by}
    return J,dict(mae=mae,corr=cor,bias=bias,resp=(resp_e,resp_c),leach=leach)
if __name__=="__main__":
    budget=int(sys.argv[1]) if len(sys.argv)>1 else 80
    pool=Pool(4);t0=time.time()
    base_t,bd=objective(pool,None,TUNE);base_h,bh=objective(pool,None,HELD)
    print('BASELINE tuning J %.3f held J %.3f'%(base_t,base_h),flush=True)
    p={k:v[0] for k,v in SPEC.items()}
    if len(sys.argv)>2 and sys.argv[2]=='resume': p=json.load(open('/tmp/w/calib_best.json'))['p'];p['knee']=max(p['knee'],0.26)
    best,detail=objective(pool,p,TUNE);n=1
    print('START J %.3f'%best,{k:round(v,3) for k,v in p.items()},flush=True)
    step={k:v[3] for k,v in SPEC.items()};log=[(n,best,dict(p))]
    while n<budget and max(step[k]/SPEC[k][3] for k in step)>0.2:
        improved=False
        keys=list(SPEC);random.shuffle(keys)
        for k in keys:
            if n>=budget:break
            for sgn in (+1,-1):
                q=dict(p);q[k]=min(SPEC[k][2],max(SPEC[k][1],p[k]+sgn*step[k]))
                if q[k]==p[k]:continue
                J,dt=objective(pool,q,TUNE);n+=1
                print('eval %2d %-5s %+d -> %.4f  (best %.4f)  %.0fs'%(n,k,sgn,q[k],J,time.time()-t0),'J %.3f'%J,flush=True)
                if J<best-1e-4:
                    best,p,detail=J,q,dt;improved=True;log.append((n,best,dict(p)))
                    json.dump(dict(best=best,p=p,log=log),open('/tmp/w/calib_best.json','w'));break
        if not improved:
            for k in step: step[k]*=0.5
            print('no improvement in a pass; halving steps',flush=True)
    ht,hd=objective(pool,p,HELD)
    out=dict(baseline_tune=base_t,baseline_held=base_h,baseline_tune_detail=bd,baseline_held_detail=bh,best_tune=best,best_held=ht,p=p,tune_detail=detail,held_detail=hd,evals=n)
    json.dump(out,open('/tmp/w/calib_final.json','w'),default=float,indent=1)
    print('FINAL tuning J %.3f (baseline %.3f)  held-out J %.3f (baseline %.3f)'%(best,base_t,ht,base_h));print({k:round(v,3) for k,v in p.items()})
    print('tuning MAE',{N:round(v,3) for N,v in detail['mae'].items()},'| baseline',{N:round(v,3) for N,v in bd['mae'].items()})
    print('held   MAE',{N:round(v,3) for N,v in hd['mae'].items()},'| baseline',{N:round(v,3) for N,v in bh['mae'].items()})
