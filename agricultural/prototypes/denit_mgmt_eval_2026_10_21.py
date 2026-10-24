import sys,numpy as np
sys.path.insert(0,'.')
import rhizo_engine as E
P=E.DENIT_SD
def load(t):
    z=np.load(f"/tmp/w/dm_{t}.npz",allow_pickle=True); A=z["A"]; return {c:A[:,i] for i,c in enumerate(z["cols"])}
def prev(a): return np.concatenate([[0],a[:-1]])
def law(D,layer,respmode="total",P=P):
    k=str(layer); th=prev(D["th_"+k]); sat=D["sat_"+k]; pwp=D["pwp_"+k]; thick=D["thick_"+k]
    bd=np.vectorize(E.sixpool_bulk_density)(sat)
    c=prev(D["no3_"+k]); s=np.clip((th-P["a"]*pwp)/(sat-P["a"]*pwp),0,1.5)
    g=1/(1+np.exp(np.clip(-(s-P["s0"])/P["sc"],-50,50)))
    resp=(D["resp_som"]+D["resp_res"])*1000.0
    if respmode=="prev": resp=prev(resp)
    f=P["K"]*resp*c/(c+P["kh"])*g
    return np.minimum(np.maximum(c*bd*thick*10.0,0),f)
yr=lambda D:(D["yeardoy"]//1000).astype(int)
def annual(D,x,y0=1983):
    m=yr(D)>=y0; return x[m].sum()/len(set(zip(D["site"][m],yr(D)[m])))
if __name__=="__main__":
    B=load("base"); I=load("irrig")
    for nm,fn in (("layer1 only",lambda D:law(D,1)),("layer1+2 (resp total each)",lambda D:law(D,1)+law(D,2)),("layer1 + 0.5*layer2",lambda D:law(D,1)+0.5*law(D,2))):
        print(f"{nm:28s} Cycles base {annual(B,B['denit']):.1f} irrig {annual(I,I['denit']):.1f} | law base {annual(B,fn(B)):.1f} irrig {annual(I,fn(I)):.1f}")
    # what changes between base and irrig, state by state (annual means over the season days)
    for k in ("no3_1","th_1","resp_som","resp_res"):
        m=yr(B)>=1983; print(k,"base %.4f irrig %.4f"%(B[k][m].mean(),I[k][m].mean()))
