import os,sys,json
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"
sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)
A=np.load('/tmp/w/ndata.npz')['A']
def L(k,j): return A[:,14+10*k+j]
mon=lambda doy: np.minimum(11,((np.asarray(doy)-1)//30.5).astype(int))
acc_e=[[[] for _ in range(12)] for _ in range(3)]; acc_c=[[[] for _ in range(12)] for _ in range(3)]
acc_te=[[[] for _ in range(12)] for _ in range(3)]; acc_tc=[[[] for _ in range(12)] for _ in range(3)]
for si,site in enumerate(SITES[:12]):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    E.DIAG_FE=[]; m.engine(site,wx,soil,cl,150,'leadin'); D=[d for d in E.DIAG_FE if d[0] is not None and d[0]>=1982]; E.DIAG_FE=None
    k=(A[:,9]==si)&(A[:,0]==150)
    for lay in range(3):
        for d in D:
            if d[2]==lay: mm=min(11,(d[1]-1)//30.5); acc_e[lay][int(mm)].append(d[5]); acc_te[lay][int(mm)].append(d[3])
        cf=L(lay,4)[k]; T=L(lay,7)[k]; doy=A[k,8]; mo=mon(doy)
        for mm in range(12): acc_c[lay][mm].extend(cf[mo==mm]); acc_tc[lay][mm].extend(T[mo==mm])
    print(site,flush=True)
for lay in range(3):
    print(f"layer {lay+1}: month | engine fE vs Cycles cf | engine T vs Cycles T")
    print("  ".join(f"{mm+1}: {np.mean(acc_e[lay][mm]):.3f}/{np.mean(acc_c[lay][mm]):.3f} ({np.mean(acc_te[lay][mm]):.1f}/{np.mean(acc_tc[lay][mm]):.1f})" for mm in range(12)))
