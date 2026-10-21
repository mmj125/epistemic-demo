import os,sys,datetime
os.environ["REGIONAL"]="0"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m, cycles_engine_validate as E
from cover_chain_2026_10_21 import corn_crop
from multiprocessing import Pool
z=np.load('/tmp/w/nb.npz',allow_pickle=True); C=z["A"]; c={k:i for i,k in enumerate(z["cols"])}
def mon(doy): return (datetime.date(2001,1,1)+datetime.timedelta(int(doy)-1)).month
def one(si):
    N=0; site=sorted(G.S)[si]; lat,lon=G.S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
    E.DIAG_NFLUX=[]; E.SIXPOOL_DIAG=[]; kw=E.standard_kwargs(soil,N)
    r=E.simulate_continuous(wx,corn_crop(cl,soil),carry_n=True,**kw)
    eng=np.zeros((12,4)); n=len(r)
    for x in E.DIAG_NFLUX: eng[mon(x[1])-1]+=[x[2],x[6]+x[7],x[8],x[5]]   # netmin, gross release, immobilization, denit
    m_=(C[:,c["site"]]==si)&(C[:,c["N"]]==N)&(C[:,c["year"]]>=1984)&(C[:,c["year"]]<=2014)
    cyc=np.zeros((12,4)); B=C[m_]
    for row in B: cyc[mon(row[c["doy"]])-1]+=[row[c["netmin"]],row[c["min"]],-row[c["imm"]],row[c["denit"]]]
    cyc/=31
    return eng/n,cyc
if __name__=="__main__":
    R=Pool(4).map(one,range(24)); e=np.mean([r[0] for r in R],0); cy=np.mean([r[1] for r in R],0)
    print("N=0, off-season windows only for the engine; Cycles all days (season months not comparable). month: netmin E|C   gross release E|C   immobilization E|C")
    for i in range(12): print(f" {i+1:2d}: {e[i,0]:6.2f} | {cy[i,0]:6.2f}     {e[i,1]:6.2f} | {cy[i,1]:6.2f}     {e[i,2]:6.2f} | {cy[i,2]:6.2f}")
