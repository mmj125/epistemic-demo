import os,sys
os.environ["REGIONAL"]="0"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m, cycles_engine_validate as E
from cover_chain_2026_10_21 import corn_crop
from multiprocessing import Pool
for _kv in filter(None,os.environ.get("NB_OVR","").split(";")):
    _k,_v=_kv.split("=",1); setattr(E,_k,eval(_v))
OUT=os.environ.get("NB_OUT","/tmp/w/nbe.npz")
def one(args):
    si,N=args; site=sorted(G.S)[si]; lat,lon=G.S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
    kw=E.standard_kwargs(soil,N); kw["record_history"]=True
    r=E.simulate_continuous(wx,corn_crop(cl,soil),carry_n=True,**kw); rows=[]
    for y,v in r.items():
        if y<1983: continue
        pd=v.get("plant_doy")
        for h in v["history"]: rows.append([si,N,y,h["doy"],h["n_no3"],h["n_nh4"],h["n_plant"],h["n_stress"],h["ag_mg_ha"],h["netmin"],h["denit"],h["leach"],h["nitr"]])
    return rows
if __name__=="__main__":
    R=Pool(4).map(one,[(s,N) for s in range(24) for N in (0,150)]); A=np.array([r for x in R for r in x]); np.savez(OUT,A=A); print(A.shape)
