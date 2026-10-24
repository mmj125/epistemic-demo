"""Management-lever pilot (REFIT_PLAN row 55): engine vs Cycles v1.5.20 on identical tile inputs for tillage (moldboard plow on the planting day, N=0 and N=150)
and irrigation (five 25 mm fixed applications, N=150). Compares the EFFECT of the lever (lever minus baseline, per year), not the yield level. Usage: python3 lever_pilot.py"""
import os,sys,json,copy,statistics,subprocess,numpy as np
os.environ.update(REGIONAL="1",LEAD_YEARS="continuous",BIGSET="/tmp/w/fresh120.json");sys.argv=['x']
import run_validation_multisite as m, rhizo_engine as E
CY=m.CY
S={k:tuple(v) for k,v in json.load(open('/tmp/w/fresh120.json')).items()}
# five sites spread over growing-season rainfall
rain={}
for k,(la,lo) in S.items():
    wx,_=m.fd.resolve_field_weather(la,lo);rain[k]=np.mean([sum(r['pp'] for d,r in wx[y].items() if 120<=d<=270) for y in wx])
ks=sorted(S,key=lambda k:rain[k]);SITES=[ks[int(i)] for i in np.linspace(3,len(ks)-4,5)]
print('sites',[(s,round(rain[s])) for s in SITES])
IRR_DOYS=(170,180,190,200,210);TILL_DOY=140
def op_for(site,N,lever):
    base=open(f"{CY}/input/{site}N{N}.operation").read()
    if lever=='till':
        a=base.index("TILLAGE");extra="TILLAGE\nYEAR                                1\nDOY                                 +0\nTOOL                                Plow_moldboard\nCROP_NAME                           N/A\nFRAC_THERMAL_TIME                   0.0\nKILL_EFFICIENCY                     0.0\n\n"
        base=base[:a]+extra+base[a:]
    if lever=='irr':
        base=base.rstrip()+"\n"+"".join("\nFIXED_IRRIGATION\nYEAR                                1\nDOY                                 %d\nVOLUME                              25          # mm\n"%d for d in IRR_DOYS)
    return base
def cycles(site,N,lever):
    tag=f"{site}N{N}{lever}"
    open(f"{CY}/input/{tag}.operation","w").write(op_for(site,N,lever))
    c=open(f"{CY}/input/{site}N{N}.ctrl").read().replace(f"{site}N{N}.operation",f"{tag}.operation");open(f"{CY}/input/{tag}.ctrl","w").write(c)
    r=subprocess.run(["./Cycles",tag],cwd=CY,capture_output=True,text=True)
    H={}
    try:
        _rows=open(f"{CY}/output/{tag}/harvest.csv").readlines()[2:]
        import shutil;shutil.rmtree(f"{CY}/output/{tag}",ignore_errors=True)
        for line in _rows:
            p=line.strip().split(",")
            if len(p)>=11: H[int(p[0][:4])]=float(p[5])
    except Exception as e: print('cycles fail',tag,r.stdout[-300:],r.stderr[-300:]);return None
    return H
_orig=m.simulate_continuous
def eng(site,wx,soil,cl,N,lever):
    wx2=copy.deepcopy(wx)
    if lever=='irr':
        for y in wx2:
            for d in IRR_DOYS:
                if d in wx2[y]: wx2[y][d]['pp']+=25.0
    if lever=='till':
        m.simulate_continuous=lambda w,c,**kw:_orig(w,c,tillage_doy='planting',tillage_implement='Plow_moldboard',**kw)
    r=m.engine(site,wx2,soil,cl,N,'leadin');m.simulate_continuous=_orig
    return {y:v['grain'] for y,v in r.items()}
out={}
for site in SITES:
    la,lo=S[site];wx,_=m.fd.resolve_field_weather(la,lo);soil,_,_=m.fd.resolve_field_soil(la,lo);cl=m.lat_of(la,lo);m.REG_LON=lo
    m.write_inputs(site,la,lo,wx,soil,cl)
    for N,lever in((0,'till'),(150,'till'),(150,'irr')):
        hb,_=m.run_cycles(site,N);hl=cycles(site,N,lever)
        if hl is None: continue
        eb=eng(site,wx,soil,cl,N,'base');el=eng(site,wx,soil,cl,N,lever)
        ys=sorted(set(hb)&set(hl)&set(eb)&set(el))
        dc=np.array([hl[y]-hb[y]['grain'] for y in ys]);de=np.array([el[y]-eb[y] for y in ys])
        out[f"{site}|N{N}|{lever}"]=dict(rain=rain[site],cyc_base=float(np.mean([hb[y]['grain'] for y in ys])),eng_base=float(np.mean([eb[y] for y in ys])),cyc_eff=float(dc.mean()),eng_eff=float(de.mean()),corr=float(np.corrcoef(dc,de)[0,1]) if dc.std()>0 and de.std()>0 else None)
        v=out[f"{site}|N{N}|{lever}"];print(site,'N%d'%N,lever,'rain %4.0f | base C %.2f E %.2f | effect C %+.2f E %+.2f | yearly corr %s'%(rain[site],v['cyc_base'],v['eng_base'],v['cyc_eff'],v['eng_eff'],None if v['corr'] is None else round(v['corr'],2)),flush=True)
json.dump(out,open('/tmp/w/lever_pilot.json','w'))
