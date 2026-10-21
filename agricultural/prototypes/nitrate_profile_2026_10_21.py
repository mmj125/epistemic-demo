import os,sys,json
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"
sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
if len(sys.argv)>1: E.NH4_LAYERED=(sys.argv[1]=="1")
S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)
A=np.load('/tmp/w/ndata.npz')['A']
res={}
def L(k,j): return A[:,14+10*k+j]
out=[]
for si,site in enumerate(SITES[:10]):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    E.DIAG_DENIT=[]; m.engine(site,wx,soil,cl,150,'leadin'); D=E.DIAG_DENIT; E.DIAG_DENIT=None
    rows=[d for d in D if d[0] is not None and d[0]>=1982]
    nl=len(rows[0][7]); eng=np.mean([d[7] for d in rows],axis=0)
    k=(A[:,9]==si)&(A[:,0]==150)
    cyc=[L(i,0)[k].mean() for i in range(4)]
    out.append((site,nl,eng,cyc))
    print(site,"engine",np.round(eng,1),"Cycles",np.round(cyc[:nl],1),flush=True)
E_=np.array([o[2][:4] if len(o[2])>=4 else np.pad(o[2],(0,4-len(o[2]))) for o in out]); C_=np.array([o[3] for o in out])
print("mean over sites: engine",np.round(E_.mean(0),1),"Cycles",np.round(C_.mean(0),1))
