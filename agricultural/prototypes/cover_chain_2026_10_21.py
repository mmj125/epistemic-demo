"""Engine corn + cereal rye cover crop against the Cycles reference (cover_ref.json from cover_ref_2026_10_21.py), 12 sites, N=0 and 150."""
import os,sys,json,copy
os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite as m, run_validation_rotation2 as r2, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)
REF=json.load(open('/tmp/w/cover_ref.json'))
def rye_crop(cl,soil_raw):
    c=dict(r2.WHEAT); c["lat_deg"]=cl; c["vern"]=dict(E.WINTER_PHENOLOGY); c["vern"]["tt_flower_pmax"]=290.0; c["base_t"]=E.WINTER_PHENOLOGY["base_t"]
    c.update(hi_x=0.0,hi_o=0.0,calibration_factor=1.0,tr_threshold_t=8.0,residue_n_from_plant=True)   # WinterRye crop-file values that differ from WinterWheat: flowering at Pmax 290, transpiration threshold 8 C; nothing is harvested
    def ml():
        L=[]
        for l in soil_raw:
            h=m.saxton_rawls(l["sand"],l["clay"],l["soc"]*m.OM_FROM_SOC)
            L.append(dict(thick=l["thick"],fc=h["fc"],pwp=h["pwp"],sat=h["sat"],theta=h["pwp"]+m.INITIAL_MOISTURE_FRACTION*(h["fc"]-h["pwp"]),ksat_mm_day=h["ksat_mm_day"],psi_e_kpa=h["psi_e_kpa"],B=h["B"]))
        return L
    c["make_layers"]=ml; return c
def corn_crop(cl,soil_raw):
    crop=dict(m.rv.CORN) if hasattr(m,'rv') else dict(m.cev.CORN); crop["lat_deg"]=cl
    def ml():
        L=[]
        for l in soil_raw:
            h=m.saxton_rawls(l["sand"],l["clay"],l["soc"]*m.OM_FROM_SOC)
            L.append(dict(thick=l["thick"],fc=h["fc"],pwp=h["pwp"],sat=h["sat"],theta=h["pwp"]+m.INITIAL_MOISTURE_FRACTION*(h["fc"]-h["pwp"]),ksat_mm_day=h["ksat_mm_day"],psi_e_kpa=h["psi_e_kpa"],B=h["B"]))
        return L
    crop["make_layers"]=ml; return crop
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    out={}
    for N in (0,150):
        kw=E.standard_kwargs(soil,N); crop=corn_crop(cl,soil)
        base=E.simulate_continuous(wx,crop,carry_n=True,**kw)
        cov=E.simulate_continuous(wx,corn_crop(cl,soil),carry_n=True,cover=dict(crop=rye_crop(cl,soil),plant_doy=288,kill_doy=105),**kw)
        def A(r): return r.get("n_leached_kg_ha",0.0)+r.get("fallow_n_leached",0.0)
        out[N]=dict(base={y:(r["grain"],A(r)) for y,r in base.items()},cov={y:(r["grain"],A(r),(r.get("cover") or {}).get("ag",float('nan')),(r.get("cover") or {}).get("n_uptake",float('nan'))) for y,r in cov.items()})
    return site,out
if __name__=="__main__":
    R=Pool(4).map(one,SITES)
    for N in (0,150):
        e_rye=[];c_rye=[];e_dy=[];c_dy=[];e_dl=[];c_dl=[];e_nup=[];c_n=[];ycb=[];lcb=[]
        persite=[]
        for site,o in R:
            ref=REF[site][str(N)]; o=o[N]; ys=[y for y in sorted(o['cov']) if y>=1983 and all(str(y) in ref[k] for k in ('rye','H','Hb','A','Ab')) and y in o['base'] and o['cov'][y][2]==o['cov'][y][2]]; nskip=[y for y in sorted(o['cov']) if y>=1983 and o['cov'][y][2]!=o['cov'][y][2]]; skipped=globals().setdefault('SK',{}); skipped[(site,N)]=len(nskip)
            er=[o['cov'][y][2] for y in ys]; cr=[ref['rye'][str(y)][0] for y in ys]
            e_rye+=er; c_rye+=cr; e_nup+=[o['cov'][y][3] for y in ys]; c_n+=[ref['rye'][str(y)][2] for y in ys]
            e_dy+=[o['cov'][y][0]-o['base'][y][0] for y in ys]; c_dy+=[ref['H'][str(y)]-ref['Hb'][str(y)] for y in ys]
            e_dl+=[o['cov'][y][1]-o['base'][y][1] for y in ys]; c_dl+=[ref['A'][str(y)]-ref['Ab'][str(y)] for y in ys]
            ycb+=[ref['Hb'][str(y)] for y in ys]; lcb+=[ref['Ab'][str(y)] for y in ys]
            persite.append((site,np.mean(er),np.mean(cr)))
        e_rye,c_rye=map(np.array,(e_rye,c_rye))
        print(f"N={N}: rye shoots at kill: engine {e_rye.mean():.2f} vs Cycles {c_rye.mean():.2f} Mg/ha, year corr {np.corrcoef(e_rye,c_rye)[0,1]:.2f}; engine N uptake {np.nanmean(e_nup):.0f} (total) vs Cycles shoot N {np.mean(c_n):.0f} kg/ha")
        print(f"   corn yield change: engine {np.mean(e_dy):+.2f} vs Cycles {np.mean(c_dy):+.2f} Mg/ha | leaching change: engine {np.mean(e_dl):+.1f} vs Cycles {np.mean(c_dl):+.1f} kg N/ha")
        print("   site-years where the engine planted no rye (corn still growing at DOY 288):",sum(v for (st,n),v in SK.items() if n==N)); print("   per-site rye (engine, Cycles):",[(s[:4],round(a,1),round(b,1)) for s,a,b in persite])
