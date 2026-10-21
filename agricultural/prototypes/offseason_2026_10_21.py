"""Off-season N budget, engine against Cycles, N=0 and 150, 24 sites (2026-10-21). Off-season = days outside the engine's season history window of each year."""
import os,sys
os.environ["REGIONAL"]="0"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m, cycles_engine_validate as E
from cover_chain_2026_10_21 import corn_crop
from multiprocessing import Pool
z=np.load('/tmp/w/nb.npz',allow_pickle=True); C=z["A"]; c={k:i for i,k in enumerate(z["cols"])}
def one(args):
    si,N=args; site=sorted(G.S)[si]; lat,lon=G.S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
    E.DIAG_NFLUX=[]; kw=E.standard_kwargs(soil,N); kw["record_history"]=True
    r=E.simulate_continuous(wx,corn_crop(cl,soil),carry_n=True,**kw)
    ys=[y for y in r if 1984<=y<=2014]
    eng=np.array([sum(x[2] for x in E.DIAG_NFLUX),sum(x[3] for x in E.DIAG_NFLUX),sum(x[4] for x in E.DIAG_NFLUX),sum(x[5] for x in E.DIAG_NFLUX)])/len(r)
    lf=np.mean([r[y].get("fallow_n_leached",0) for y in ys]); df=np.mean([r[y].get("fallow_n_denitrified",0) for y in ys]); vf=np.mean([r[y].get("fallow_n_volatilized",0) for y in ys])
    cy=[]
    for y in ys:
        h=r[y]["history"]; d0,d1=h[0]["doy"],h[-1]["doy"]
        m_=(C[:,c["site"]]==si)&(C[:,c["N"]]==N)&(C[:,c["year"]]==y)&((C[:,c["doy"]]<d0)|(C[:,c["doy"]]>d1))
        B=C[m_]
        cy.append([B[:,c["netmin"]].sum(),B[:,c["nitr"]].sum(),B[:,c["volat"]].sum(),B[:,c["denit"]].sum(),B[:,c["leach_no3"]].sum()+B[:,c["leach_nh4"]].sum()+B[:,c["bypass"]].sum()])
    return N,eng,[lf,df,vf],np.mean(cy,0)
if __name__=="__main__":
    R=Pool(4).map(one,[(s,N) for s in range(24) for N in (0,150)])
    for N in (0,150):
        e=np.mean([r[1] for r in R if r[0]==N],0); f=np.mean([r[2] for r in R if r[0]==N],0); cy=np.mean([r[3] for r in R if r[0]==N],0)
        print(f"N={N} off-season per year (kg N/ha): net mineralization engine {e[0]:.1f} Cycles {cy[0]:.1f} | nitrification {e[1]:.1f} vs {cy[1]:.1f} | volatilization {e[2]:.1f} (window {f[2]:.1f}) vs {cy[2]:.1f} | denitrification {e[3]:.1f} (window {f[1]:.1f}) vs {cy[3]:.1f} | leaching {f[0]:.1f} vs {cy[4]:.1f}")
