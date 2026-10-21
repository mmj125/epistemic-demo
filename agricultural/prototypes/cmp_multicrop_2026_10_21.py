import json,glob,numpy as np,sys
def load(pre):
    D={}
    for f in glob.glob(f'/tmp/w/{pre}_[0-3].json'): D.update(json.load(open(f)))
    return D
B=load(sys.argv[1]); N=load(sys.argv[2]); rng=np.random.default_rng(0)
sites=sorted(set(k.split('|')[0] for k in B)&set(k.split('|')[0] for k in N)); print(sys.argv[2],'vs',sys.argv[1],len(sites),'sites')
levels=sorted(set(int(k.split('|')[1][1:]) for k in B))
for n in levels:
    mb=[];mn=[];bb=[];bn=[];pb=[];pn=[];tot={}
    for s in sites:
        k=f'{s}|N{n}|leadin'
        if k not in B or k not in N: continue
        for D,m_,b_,pp in ((B,mb,bb,pb),(N,mn,bn,pn)):
            p=np.array(D[k]['res']['grain']['pairs']); m_.append(np.abs(p[:,1]-p[:,0]).mean()); b_.append((p[:,1]-p[:,0]).mean()); pp.append(p)
        for v in ('leach','denit','volat','n2o'):
            for tag,D in (('B',B),('N',N)):
                r=D[k]['res'][v]; tot.setdefault((v,tag),[]).append((r['real'],r['model']))
    mb,mn=map(np.array,(mb,mn)); d=mb-mn; bs=d[rng.integers(0,len(d),(4000,len(d)))].mean(1)
    cb=np.corrcoef(np.vstack(pb).T)[0,1]; cn=np.corrcoef(np.vstack(pn).T)[0,1]
    loss=[]
    for v in ('leach','denit','volat','n2o'):
        a=np.array(tot[(v,'B')]); b=np.array(tot[(v,'N')]); f=lambda x:np.sqrt(np.mean((np.log(x[:,1]+.5)-np.log(x[:,0]+.5))**2))
        loss.append(f"{v} x{a[:,1].mean()/max(a[:,0].mean(),1e-9):.2f}->x{b[:,1].mean()/max(b[:,0].mean(),1e-9):.2f} rmslog {f(a):.2f}->{f(b):.2f}")
    print(f' N={n}: grain MAE {mb.mean():.3f}->{mn.mean():.3f} gain {d.mean():+.3f} [{np.percentile(bs,2.5):+.3f},{np.percentile(bs,97.5):+.3f}] bias {np.mean(bb):+.3f}->{np.mean(bn):+.3f} pooled r {cb:.3f}->{cn:.3f} | '+' | '.join(loss))
