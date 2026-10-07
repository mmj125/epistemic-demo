"""Wheat chain harness (2026-10-07). Needs a local Cycles v1.4.4 ContinuousWheat run (input/ContinuousWheat.operation:
PLANTING DOY 288, WinterWheat, plus a 90 kg/ha UAN at DOY 75, ROTATION_SIZE 1, otherwise the ContinuousCorn .ctrl) under
REFERENCE_DATA_DIR. Runs each wheat season with N and carbon state carried from prior seasons and a summer-fallow N window.
Env: PL=1 per-layer six-pool and per-layer nitrate, LEAD=prior seasons, CARRYC=1 carry carbon state. Not committed outputs.
"""
import sys,statistics as st,math,copy,os
sys.path.insert(0,"/home/user/epistemic-demo/agricultural/prototypes")
import run_validation_rotation2 as r
import cycles_engine_validate as cev
from cycles_engine_validate import *
PL=os.environ.get("PL","0")=="1"; LEAD=int(os.environ.get("LEAD","2")); CARRYC=os.environ.get("CARRYC","1")=="1"
_,wf=r.load_weather(); fi={(y,d):i for i,(y,d,_) in enumerate(wf)}
real=r.real_harvest("ContinuousWheat","WinterWheat")
rowsof=lambda a,b:[x for (_,_,x) in wf[a:b]]
def run_chain(py):  # py = planting calendar year of the target season
    layers=r.WHEAT["make_layers"](); nstate=None; sp=None; prev_end=None
    for y in range(max(1980,py-LEAD),py+1):
        start=fi[(y,288 if (y,288) in fi else 288)]
        if prev_end is None:
            j=fi[(y,1)]; fallow=rowsof(j,start)
        else: fallow=rowsof(prev_end,start)
        if nstate is None:
            nstate=dict(n_nh4=0.0,n_no3=0.0,tsoil_lag=(wf[start][2]["tx"]+wf[start][2]["tn"])/2.0,no3_layers=([0.0]*len(layers) if PL else None))
        de=dict(de=0.0,tew=compute_tew(layers[0]["fc"],layers[0]["pwp"]),rew=REW_DEFAULT_MM)
        run_fallow_n_window(layers,fallow,nstate,sp,lat_deg=r.WHEAT["lat_deg"],de_state=de,model_denitrification=True,model_volatilization=True)
        nstate.pop("n2o",None)
        kw=dict(initial_n_state=dict(nstate),initial_layers=layers,spinup_rows=None,n_applications=[(75,90)],
                wue_co2_scale=CO2_PPM_BY_YEAR.get(y,CO2_REF_PPM)/CO2_REF_PPM,record_history=True,nh4_no3_split=True,
                background_n_model="sixpool",sixpool_topsoil_clay_pct=r.SOIL_LAYERS_RAW[0]["clay"],sixpool_topsoil_soc_pct=r.SOIL_LAYERS_RAW[0]["soc"],
                model_denitrification=True,model_volatilization=True,sixpool_profile_raw=r.SOIL_LAYERS_RAW if PL else None,sixpool_per_layer=PL,nitrate_per_layer=PL,fertilizer_source='uan')
        if sp is not None and CARRYC: kw["sixpool_initial_state"]=sp
        res=simulate_season(rowsof(start,start+400),r.WHEAT,**kw)
        layers=res["final_layers"]; nstate=dict(res["final_n_state"]); sp=copy.deepcopy(res.get("sixpool_final_state"))
        prev_end=start+len(res["history"])
    return res
if __name__=="__main__":
    def corr(a,b):
        ma,mb=st.mean(a),st.mean(b); return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    rv=[];mv=[];m0=[]
    for hy,info in sorted(real.items()):
        res=run_chain(info["plant_year"])
        h=res["history"]; e0=h[0]["n_pool"]; mm=[x for x in h if x["doy"]==60]
        rv.append(info["grain"]); mv.append(res["grain"]); m0.append(mm[0]["n_pool"] if mm else 0)
    import datetime
    Nn={}
    for l in open("/tmp/cycles-run/output/ContinuousWheat/N.txt").read().split("\n")[2:]:
        q=l.split("\t")
        if len(q)>12: Nn[q[0][:10]]=float(q[2])+float(q[3])
    ys=[hy for hy,_ in sorted(real.items())]
    for i,hy in enumerate(ys): print(hy,"yield real %.2f eng %.2f | Mar1 mineralN real %.0f eng %.0f"%(rv[i],mv[i],Nn.get(f"{hy}-03-01",-1),m0[i]))
    print("corr Mar1 N real-vs-eng %.3f"%corr([Nn.get(f"{hy}-03-01",0) for hy in ys],m0))
    print("LEAD",LEAD,"real mean %.2f eng mean %.2f MAE %.2f corr %.3f  engine Mar1 mineralN mean %.1f"%(st.mean(rv),st.mean(mv),st.mean(abs(a-b) for a,b in zip(rv,mv)),corr(rv,mv),st.mean(m0)))
