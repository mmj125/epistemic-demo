"""Rebuild phase 6 (2026-10-16): continuous winter wheat, engine vs Cycles v1.5.20 on identical tile inputs, many sites, standard configuration.
Wheat is planted DOY 288 and harvested the next summer; 90 kg N/ha UAN at DOY 75 is the Cycles sample's own rate, 0 and 150 bracket it.
Reports the engine with its calibration_factor AND with it forced to 1.0, so a mask cannot hide the gap. Usage: NSITES=30 python3 run_validation_multisite_wheat.py"""
import os,sys,json,math,shutil,statistics as st,copy
os.environ["N_LEVELS"]="0,90,150"; os.environ.setdefault("REGIONAL","0")
sys.path.insert(0,'.')
import run_validation_multisite as m, run_validation_rotation2 as r2, rhizo_engine as E
from multiprocessing import Pool
CY=m.CY
OP='''PLANTING
YEAR                1
DOY                 288
END_DOY             -999
CROP                WinterWheat
MAX_SMC             -999
MIN_SMC             0.0
MAX_SOIL_TEMP       -999
MIN_SOIL_TEMP       0.0
USE_AUTO_IRR        0
USE_AUTO_FERT       0
DENSITY             1.0
CLIPPING_START      1
CLIPPING_END        366
MAXIMUM_SOIL_COVERAGE               100         # (%)
STANDING_RESIDUE_AT_HARVEST         40          # (%)
RESIDUE_REMOVED                     0           # (%)
CLIPPING_BIOMASS_THRESHOLD_LOWER    0.5         # (Mg/ha)
CLIPPING_BIOMASS_THRESHOLD_UPPER    999         # (Mg/ha)
CLIPPING_BIOMASS_DESTINY            RETURN      # (-)
HARVEST_TIMING                      -999        # (%)
KILL_AFTER_HARVEST                  1           # (-)
'''
FERT='''
FIXED_FERTILIZATION
YEAR                                1
DOY                                 75
SOURCE                              32-00-00_Urea_Ammonium_Nitrate_Solution
MASS                                %.2f      # kg/ha
FORM                                Liquid
METHOD                              Broadcast
DEPTH                               0.05        # m
'''
def cycles_annual(fsite,N):
    """Cycles' calendar-year N losses {year: dict(leach, denit, volat, n2o)} from the same cache (added 2026-10-23 so the wheat runs can score N losses)."""
    cache=f"{CY}/cache15_{fsite}N{N}.json"
    return {int(k):v for k,v in json.load(open(cache))["A"].items()}
def cycles_ref(fsite,N):
    cache=f"{CY}/cache15_{fsite}N{N}.json"
    if os.path.exists(cache):
        d=json.load(open(cache)); return {int(k):v for k,v in d["H"].items()}
    subprocess_out=m._run_cycles_uncached(fsite,N)
    H,A=subprocess_out; json.dump(dict(H=H,A=A),open(cache,"w"))
    shutil.rmtree(f"{CY}/output/{fsite}N{N}",ignore_errors=True)   # disk is the limit
    return H
FALLN=float(os.environ.get("FALLN","0"))   # 2026-10-17: starter N at planting (kg N/ha, of the total N); the spring-only schedule starves winters after big-residue years and flips Cycles between failed and good years (bistable), which makes yearly metrics a phase artifact
def fert_text(N):
    if N<=0: return ""
    sp=N-FALLN if N>FALLN else N; t=FERT%(sp/0.32)
    if FALLN>0 and N>FALLN: t+=FERT.replace("DOY                                 75","DOY                                 289")%(FALLN/0.32)
    return t
def engine_chain(wx,soil,cl,N,calib):
    crop=dict(r2.WHEAT); crop["lat_deg"]=cl; 
    if os.environ.get("WINTERKILL"): crop["winterkill_temp"]=float(os.environ["WINTERKILL"])   # 2026-10-18: off by default; the -25 layer-1 soil proxy (derived from 3 Rock Springs winters, no snow insulation) over-kills elsewhere: with the water mechanism pooled correlation 0.921/0.664/0.678 (kill -25) vs 0.945/0.708/0.729 (none) at N=0/90/150
    if os.environ.get("WHEAT_VERN","1")=="1":   # disclosed winter phenology (vernalization, photoperiod, grain filling); 0 = the old single-threshold phenology
        crop["vern"]=dict(E.WINTER_PHENOLOGY); crop["base_t"]=E.WINTER_PHENOLOGY["base_t"]
    if calib is not None: crop["calibration_factor"]=calib
    if os.environ.get("WHEAT_RHIZO","1")=="1": crop["rhizo_rr"]=0.6; crop["rhizo_root_n_share"]=0.082   # 2026-10-22: Cycles' wheat budget loses 5.7% of plant N beyond the plant's own; (0.4/0.6) x root N share 0.082 = 5.5%
    def ml():
        L=[]
        for l in soil:
            h=m.saxton_rawls(l["sand"],l["clay"],l["soc"]*m.OM_FROM_SOC)
            L.append(dict(thick=l["thick"],fc=h["fc"],pwp=h["pwp"],sat=h["sat"],theta=h["pwp"]+m.INITIAL_MOISTURE_FRACTION*(h["fc"]-h["pwp"]),ksat_mm_day=h["ksat_mm_day"],psi_e_kpa=h["psi_e_kpa"],B=h["B"]))
        return L
    crop["make_layers"]=ml
    for _o in os.environ.get("CROPOVR","").split(";"):   # per-run crop overrides, NAME=VALUE;NAME=VALUE
        if _o: _k,_v=_o.split("=",1); crop[_k]=eval(_v)
    wf=[(y,d,wx[y][d]) for y in sorted(wx) for d in sorted(wx[y])]; fi={(y,d):i for i,(y,d,_) in enumerate(wf)}; rows=lambda a,b:[x for (_,_,x) in wf[a:b]]
    layers=ml(); nstate=None; sp=None; prev_end=None; out={}
    base=E.standard_kwargs(soil,0); base.pop("fertilizer_source",None); base["n_rate_kg_ha"]=None
    for y in sorted(wx)[:-1]:
        if (y,288) not in fi: continue
        start=fi[(y,288)]
        fallow=rows(fi[(y,1)],start) if prev_end is None else rows(prev_end,start)
        if nstate is None:
            nstate=dict(n_nh4=0.0,n_no3=0.0,tsoil_lag=(wf[start][2]["tx"]+wf[start][2]["tn"])/2.0,no3_layers=[0.0]*len(layers),rel_hist=[])
        de=dict(de=0.0,tew=E.compute_tew(layers[0]["fc"],layers[0]["pwp"]),rew=E.REW_DEFAULT_MM)
        E._DIAG_YEAR=y
        E._FORCE_CUR=(E.FORCE_SERIES.get(y) if E.FORCE_SERIES else None)
        _fl=E.run_fallow_n_window(layers,fallow,nstate,sp,lat_deg=cl,de_state=de,model_denitrification=True,model_volatilization=True)
        _fn2o=nstate.pop("n2o",0.0)
        kw=dict(base); kw.update(initial_n_state=dict(nstate),initial_layers=layers,spinup_rows=None,wue_co2_scale=(E.CO2_PPM_BY_YEAR.get(y,E.CO2_REF_PPM)/E.CO2_REF_PPM)**crop.get('wue_co2_exp',E.WUE_CO2_EXP),rue_co2_scale=(E.CO2_PPM_BY_YEAR.get(y,E.CO2_REF_PPM)/E.CO2_REF_PPM)**crop.get('rue_co2_exp',E.RUE_CO2_EXP),record_history=True)
        if N>0: kw["n_applications"]=([(289,FALLN),(75,N-FALLN)] if (FALLN>0 and N>FALLN) else [(75,N)]); kw["fertilizer_source"]="uan"
        else: kw["n_rate_kg_ha"]=0
        if sp is not None: kw["sixpool_initial_state"]=sp
        if os.environ.get("WHEAT_SEASON_CLOCK","1")=="1":   # 2026-10-23: pre-pass for the season's own maturity thermal time (TTf = tt / tt at maturity, paper Sec 2.3); state is copied so the pass leaves nothing behind
            _k=dict(kw); _k["initial_n_state"]=dict(nstate); _k["initial_layers"]=copy.deepcopy(layers); _k["record_history"]=False
            if sp is not None: _k["sixpool_initial_state"]=copy.deepcopy(sp)
            _p=E.simulate_season(rows(start,start+400),crop,**_k); _c=dict(crop); _c["season_tt_end"]=_p["tt_cum_end"]
        else: _c=crop
        res=E.simulate_season(rows(start,start+400),_c,**kw)
        layers=res["final_layers"]; nstate=dict(res["final_n_state"]); sp=copy.deepcopy(res.get("sixpool_final_state"))
        prev_end=start+len(res["history"]); out[y+1]=res
        res["loss"]=dict(leach=_fl[0]+res.get("n_leached_kg_ha",0.0),denit=_fl[1]+res.get("n_denitrified_kg_ha",0.0),volat=_fl[2]+res.get("n_volatilized_pool_kg_ha",0.0),n2o=_fn2o+res.get("n2o_emitted_kg_ha",0.0))   # the fallow window before planting plus the season (2026-10-23)
    return out
def corr(a,b):
    ma,mb=st.mean(a),st.mean(b); sa=math.sqrt(sum((x-ma)**2 for x in a)); sb=math.sqrt(sum((x-mb)**2 for x in b)); return sum((a[i]-ma)*(b[i]-mb) for i in range(len(a)))/(sa*sb) if sa and sb else float('nan')
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"+("F%d"%FALLN if FALLN else ""); m.write_inputs(fs,lat,lon,wx,soil,cl); res={}
    for N in (0,90,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(OP+fert_text(N))   # 2026-10-18: the Cycles reference now gets the same fall + spring N as the engine (was spring-only, which flips Cycles between failed and good years)
        H=cycles_ref(fs,N)
        for tag,calib in (("calib",None),("raw",1.0)):
            R=engine_chain(wx,soil,cl,N,calib); ys=[y for y in sorted(set(H)&set(R)) if y>1981]
            row={}
            for v,hk,rk in (("grain","grain","grain"),("total_biomass","total","total")):
                x=[H[y][hk] for y in ys]; z=[R[y][rk] for y in ys]
                row[v]=dict(real=st.mean(x),model=st.mean(z),mae=st.mean(abs(i-j) for i,j in zip(x,z)),corr=corr(x,z),n=len(ys),pairs=[[round(i,4),round(j,4)] for i,j in zip(x,z)])
            if tag=="calib":
                A=cycles_annual(fs,N); yc=[y for y in range(1982,2016) if y in A]; ye=[y for y in ys if "loss" in R[y]]
                for q in ("leach","denit","volat","n2o"):   # mean annual kg N/ha: engine over its seasons (fallow before planting included, about 35 years) against Cycles' calendar years 1982 to 2015
                    row[q]=dict(real=st.mean(A[y][q] for y in yc),model=sum(R[y]["loss"][q] for y in ye)/len(ye)*len(ye)/35.0)
            res[f"N{N}|{tag}"]=row
    return site,name,res
if __name__=="__main__":
    S=json.load(open('sitesets/fresh94.json')); ks=sorted(S); n=int(os.environ.get("NSITES","30")); ks=[ks[i] for i in range(int(os.environ.get('SITEOFF','0')),len(ks),max(1,len(ks)//n))][:n]   # SITEOFF=1 or 2 gives a disjoint stride set
    with Pool(int(os.environ.get("NPROC","4"))) as p: R=p.map(one,[(k,S[k]) for k in ks])
    json.dump(R,open(os.environ.get("OUT_JSON","/tmp/w/wheat_ms.json"),"w"))
    for N in (0,90,150):
        for tag in ("calib","raw"):
            for v in ("grain","total_biomass"):
                a=[o[f"N{N}|{tag}"][v] for _,_,o in R]
                print(f"wheat N={N} {tag:5s} {v:13s} Cycles {st.mean(x['real'] for x in a):5.2f} MAE {st.mean(x['mae'] for x in a):5.2f} ({100*st.mean(x['mae'] for x in a)/st.mean(x['real'] for x in a):.0f}%) bias {st.mean(x['model']-x['real'] for x in a):+.2f} corr {st.mean(x['corr'] for x in a if x['corr']==x['corr']):.2f}")
