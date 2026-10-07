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
def corr(a,b):
    import statistics as st,math
    ma,mb=st.mean(a),st.mean(b); return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))


def full_chain():
    """One continuous 1980-2016 chain (soil water, mineral N, six-pool carbon carried across every season and the
    summer fallow between them), like Cycles' own continuous run. Returns {harvest_year: simulate_season result}.
    With crop["winterkill_temp"]=-25 it kills the stand in exactly Cycles' three winters (1982, 1985, 1994)."""
    layers=r.WHEAT["make_layers"](); nstate=None; sp=None; prev_end=None; out={}
    for y in range(1980,2016):
        start=fi[(y,288)]
        fallow=rowsof(fi[(y,1)],start) if prev_end is None else rowsof(prev_end,start)
        if nstate is None:
            nstate=dict(n_nh4=0.0,n_no3=0.0,tsoil_lag=(wf[start][2]["tx"]+wf[start][2]["tn"])/2.0,no3_layers=[0.0]*len(layers))
        de=dict(de=0.0,tew=compute_tew(layers[0]["fc"],layers[0]["pwp"]),rew=REW_DEFAULT_MM)
        run_fallow_n_window(layers,fallow,nstate,sp,lat_deg=r.WHEAT["lat_deg"],de_state=de,model_denitrification=True,model_volatilization=True)
        nstate.pop("n2o",None)
        kw=dict(initial_n_state=dict(nstate),initial_layers=layers,spinup_rows=None,n_applications=[(75,90)],
                wue_co2_scale=CO2_PPM_BY_YEAR.get(y,CO2_REF_PPM)/CO2_REF_PPM,record_history=True,nh4_no3_split=True,
                background_n_model="sixpool",sixpool_topsoil_clay_pct=r.SOIL_LAYERS_RAW[0]["clay"],sixpool_topsoil_soc_pct=r.SOIL_LAYERS_RAW[0]["soc"],
                model_denitrification=True,model_volatilization=True,sixpool_profile_raw=r.SOIL_LAYERS_RAW,sixpool_per_layer=True,nitrate_per_layer=True,fertilizer_source='uan')
        if sp is not None: kw["sixpool_initial_state"]=sp
        res=simulate_season(rowsof(start,start+400),r.WHEAT,**kw)
        layers=res["final_layers"]; nstate=dict(res["final_n_state"]); sp=copy.deepcopy(res.get("sixpool_final_state"))
        prev_end=start+len(res["history"]); out[y+1]=res
    return out


if __name__=="__main__":
    import statistics as st
    WHEAT=r.WHEAT; WHEAT["winterkill_temp"]=-25.0
    out=full_chain()
    ys=[y for y in sorted(real) if y in out]
    rv=[real[y]["grain"] for y in ys]; mv=[out[y]["grain"] for y in ys]
    print("full chain: real mean %.2f engine mean %.2f corr %.3f killed %s"%(st.mean(rv),st.mean(mv),corr(rv,mv),[y for y in out if out[y].get("winter_killed")]))
