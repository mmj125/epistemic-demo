import os,sys,json
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"
sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
if len(sys.argv)>1: E.NH4_LAYERED=(sys.argv[1]=="1")
S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)
A=np.load('/tmp/w/ndata.npz')['A']
def L(k,j): return A[:,14+10*k+j]
rows=[]
for si,site in enumerate(SITES[:12]):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    E.DIAG_NSEASON=[]; m.engine(site,wx,soil,cl,150,'leadin'); D=[d for d in E.DIAG_NSEASON if d[0] is not None and d[0]>=1982]; E.DIAG_NSEASON=None
    k=(A[:,9]==si)&(A[:,0]==150)
    key={(int(y),int(d)):i for i,(y,d) in enumerate(zip(A[k,10],A[k,8]))}
    idx=[key[(d[0],d[1])] for d in D if (d[0],d[1]) in key]
    dd=[d for d in D if (d[0],d[1]) in key]
    ye=len(set(d[0] for d in dd))
    e=np.array([[x[2],x[3],x[4],x[5],x[6],x[7]] for x in dd]).sum(0)/ye   # netmin, nitrif, volat, denit, leach, uptake per year in season days
    sel=np.where(k)[0][idx]
    c=dict(nit=A[sel,1].sum()/ye,vol=A[sel,2].sum()/ye,den=A[sel,3].sum()/ye)
    pool_e=np.mean([x[8] for x in dd]); pool_c=np.mean(sum(L(i,0)[sel]+L(i,1)[sel] for i in range(4)))
    rows.append((e,c,pool_e,pool_c))
    print(site,"engine netmin %.0f nit %.0f vol %.1f den %.1f leach %.0f upt %.0f pool %.0f | Cycles nit %.0f vol %.1f den %.1f pool %.0f"%(*e,pool_e,c['nit'],c['vol'],c['den'],pool_c),flush=True)
E_=np.mean([r[0] for r in rows],axis=0); print("MEAN engine netmin %.0f nit %.0f vol %.1f den %.1f leach %.0f upt %.0f | Cycles nit %.0f vol %.1f den %.1f | pools engine %.0f Cycles %.0f"%(*E_,np.mean([r[1]['nit'] for r in rows]),np.mean([r[1]['vol'] for r in rows]),np.mean([r[1]['den'] for r in rows]),np.mean([r[2] for r in rows]),np.mean([r[3] for r in rows])))
