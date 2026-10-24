"""Fertilizer-N recovery and N losses by site, engine vs Cycles, N=150 (2026-10-15). Usage: python3 recovery_check.py"""
import sys,os,csv,json,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, rhizo_engine as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
def cyc(site,N):
    A=[x for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/annualN.csv')) if x['year'][0]!='#']
    H={int(x['date'][:4]):(float(x['grain_yield']),float(x['total_nitrogen'])) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')) if x['date'][0]!='#'}
    loss=np.mean([float(x['NO3_leaching'])+float(x['NH4_leaching'])+float(x['denitrification'])+float(x['volatilization'])+float(x['N2O_emission']) for x in A])
    return loss,np.mean([v[1] for v in H.values()]),np.mean([v[0] for v in H.values()])
def one(site):
    lat,lon=S.ALL[site];wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    out={}
    for N in (0,150):
        r=m.engine(site,wx,soil,cl,N,'leadin')
        loss=np.mean([r[y].get('n_leached_kg_ha',0)+r[y].get('n_denitrified_kg_ha',0)+r[y].get('n_volatilized_pool_kg_ha',0)+r[y].get('n2o_emitted_kg_ha',0) for y in r])
        out[N]=(loss,np.mean([r[y]['n_uptake_kg_ha'] for y in r]),np.mean([r[y]['grain'] for y in r]))
    return site,out,{N:cyc(site,N) for N in (0,150)}
if __name__=="__main__":
    with Pool(4) as p:R=p.map(one,list(S.ALL))
    json.dump(R,open('/tmp/w/recovery.json','w'),default=float)
    rows=[]
    for s,e,c in R:
        recE=(e[150][1]-e[0][1])/150;recC=(c[150][1]-c[0][1])/150
        lossE=e[150][0]-e[0][0];lossC=c[150][0]-c[0][0]
        rows.append((s,recE,recC,lossE,lossC,e[150][2]-c[150][2],c[0][2]))
    A=np.array([r[1:] for r in rows])
    print('mean fertilizer recovery (plant N gain / 150): engine %.2f  Cycles %.2f ; fertilizer-attributable loss kg/ha: engine %.1f  Cycles %.1f'%(A[:,0].mean(),A[:,1].mean(),A[:,2].mean(),A[:,3].mean()))
    print('corr(bias150, recovery gap eng-cyc) %+.2f ; corr(bias150, loss gap cyc-eng) %+.2f ; corr(bias150, Cycles N0 yield) %+.2f'%(np.corrcoef(A[:,4],A[:,0]-A[:,1])[0,1],np.corrcoef(A[:,4],A[:,3]-A[:,2])[0,1],np.corrcoef(A[:,4],A[:,5])[0,1]))
    for r in sorted(rows,key=lambda t:-t[5])[:8]:print('  %-12s rec eng %.2f cyc %.2f | fert loss eng %5.1f cyc %5.1f | bias150 %+.2f | Cycles N0 yield %.1f'%(r[0],r[1],r[2],r[3],r[4],r[5],r[6]))
