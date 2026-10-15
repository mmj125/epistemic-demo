"""Designed fertilized-corn experiment: engine vs Cycles v1.5.20 on identical synthetic inputs (2026-10-15, REFIT_PLAN row 44).
Seasonal temperature cycle, constant daily rain, factorial mean temperature x rain x SOC x clay x N rate, 8 years. Uses the multi-site harness's own
Cycles input writer, parser and engine call so the setup is the same as the real-site runs. Usage: python3 designed_crop.py OUT.json"""
import sys,os,json,itertools,math
os.environ["REGIONAL"]="0";os.environ["LEAD_YEARS"]="continuous"
import numpy as np
sys.path.insert(0,'.')
import run_validation_multisite as m
YRS=list(range(1981,1989));TH=[0.2,0.2,0.3,0.3,0.5,0.5]
TMS=[8,12,16];RAINS=[1.5,3.0];SOCS=[1.0,2.5];CLAYS=[15,40];NS=[0,75,150,300]
def wx_of(Tm,rain):
    wx={}
    for y in YRS:
        wx[y]={}
        for d in range(1,366):
            T=Tm+12*math.sin(2*math.pi*(d-110)/365);sol=14+9*math.sin(2*math.pi*(d-80)/365)
            wx[y][d]=dict(doy=d,pp=rain,tx=T+5,tn=T-5,solar=sol,rhx=85.0,rhn=45.0,wind=2.5)
    return wx
def soil_of(soc0,clay):
    out=[];z=0.0
    for t in TH:
        z+=t/2;out.append(dict(thick=t,clay=float(clay),sand=float(max(5,70-clay-10)),soc=max(0.1,soc0*math.exp(-z/0.5))));z+=t/2
    return out
if __name__=="__main__":
    m.N_LEVELS=NS;res=[]
    for Tm,rain,soc0,clay in itertools.product(TMS,RAINS,SOCS,CLAYS):
        site=f"dx_{Tm}_{int(rain*10)}_{int(soc0*10)}_{clay}";wx=wx_of(Tm,rain);soil=soil_of(soc0,clay)
        m.write_inputs(site,40.0,-90.0,wx,soil,40.0)
        for N in NS:
            p=f"{m.CY}/input/{site}N{N}.ctrl";c=open(p).read().replace('SIMULATION_START_YEAR   1980','SIMULATION_START_YEAR   1981').replace('SIMULATION_END_YEAR     2016','SIMULATION_END_YEAR     1988');open(p,'w').write(c)
        for N in NS:
            H,A=m._run_cycles_uncached(site,N)
            E=m.engine(site,wx,soil,40.0,N,'leadin')
            ys=[y for y in YRS if y in H and y in E and y>=YRS[1]]
            def mean(f):return float(np.mean([f(y) for y in ys]))
            r=dict(Tm=Tm,rain=rain,soc0=soc0,clay=clay,N=N,
                   cy=dict(grain=mean(lambda y:H[y]['grain']),total=mean(lambda y:H[y]['total']),leach=mean(lambda y:A[y]['leach']),denit=mean(lambda y:A[y]['denit']),volat=mean(lambda y:A[y]['volat']),n2o=mean(lambda y:A[y]['n2o'])),
                   en=dict(grain=mean(lambda y:E[y]['grain']),total=mean(lambda y:E[y]['total']),leach=mean(lambda y:E[y].get('n_leached_kg_ha',0)),denit=mean(lambda y:E[y].get('n_denitrified_kg_ha',0)),volat=mean(lambda y:E[y].get('n_volatilized_pool_kg_ha',0)),n2o=mean(lambda y:E[y].get('n2o_emitted_kg_ha',0))))
            res.append(r);print(site,N,'grain cy %.2f en %.2f | leach cy %.1f en %.1f | denit cy %.1f en %.1f'%(r['cy']['grain'],r['en']['grain'],r['cy']['leach'],r['en']['leach'],r['cy']['denit'],r['en']['denit']),flush=True)
    json.dump(res,open(sys.argv[1],'w'))
