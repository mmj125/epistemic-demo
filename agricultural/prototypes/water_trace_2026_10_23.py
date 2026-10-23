"""Matched-input trace of the engine's water stress formula (2026-10-23). Corn, 24 sites, N=150, continuous chain. For every growing-season day Cycles' own layer moisture, canopy interception and potential transpiration
are fed to the engine's campbell_water_uptake (same soil layers the engine uses), and the resulting stress factor (actual / potential transpiration) is compared with Cycles' own (1 - water_stress/100). If the two agree the
engine's formula is not the problem and its soil water STATE is; if not, the formula or its inputs (root depth, root distribution, conductance) differ. Variants: moisture at the start of day (previous end of day) or the end of day;
root depth as the engine grows it or at full depth; Usage: python3 water_trace_2026_10_23.py"""
import os,sys,json,csv,shutil,subprocess,datetime,copy
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    C=rd(d+"dailyCornRM.90.csv"); W=rd(d+"dailyWater.csv"); shutil.rmtree(d,ignore_errors=True)
    crop=dict(rv.CORN); wumax=crop["tr_max_mm_day"]; ct=E.total_root_conductance(wumax,crop["lwp_stress_onset"])
    base=[]
    for l in soil:
        h=m.saxton_rawls(l["sand"],l["clay"],l["soc"]*m.OM_FROM_SOC)
        base.append(dict(thick=l["thick"],fc=h["fc"],pwp=h["pwp"],sat=h["sat"],ksat_mm_day=h["ksat_mm_day"],psi_e_kpa=h["psi_e_kpa"],B=h["B"]))
    rows=[]; prev=None
    nl=len(base)
    for c,w in zip(C,W):
        th=[float(w.get(f"soil_moisture_content.{i+1}",0) or 0) for i in range(nl)]
        if c['biomass']=='-999' or c['stage'] not in ('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH'):
            prev=th; continue
        trp=float(c['potential_transpiration']); ci=float(c['radiation_interception']); ws=1-float(c['water_stress'])/100; ttf=float(c['thermal_time'])/crop["tt_maturity"]
        tra=float(w['transpiration'])
        if trp>0.2 and ci>0.02 and prev is not None:
            out=[]
            for mode in ("start","end"):
                for rootmode in ("grown","full"):
                    L=copy.deepcopy(base)
                    for i_,(l,t) in enumerate(zip(L,(prev if mode=="start" else th))): l["theta"]=max(l["pwp"],t-(float(os.environ.get("SHIFT","0")) if i_<2 else 0.0))
                    rd_=crop["root_max_m"]*(min(1.0,ttf/E.ROOT_TTF_FULL) if rootmode=="grown" else 1.0)
                    tr,st=E.campbell_water_uptake(L,rd_,trp,ci,ct,crop["lwp_stress_onset"],crop["lwp_wilting_point"])
                    out.append(st)
            rows.append([ttf,trp,ci,ws,tra/trp]+out)
        prev=th
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); np.save('/tmp/w/water_trace_'+os.environ.get('SHIFT','0')+'.npy',A)
    print(len(A),"days; columns ttf,trp,ci,cycles_stress_factor,cycles_TR/TRp, then engine stress from (start,grown),(start,full),(end,grown),(end,full)")
    names=["start/grown","start/full","end/grown","end/full"]
    print(f"all days: Cycles mean factor {A[:,3].mean():.3f}  (TR/TRp {A[:,4].mean():.3f})")
    for j,nm in enumerate(names):
        e=A[:,5+j]; print(f"  {nm:12s}: engine mean {e.mean():.3f} bias {np.mean(e-A[:,3]):+.3f} rms {np.sqrt(np.mean((e-A[:,3])**2)):.3f} corr {np.corrcoef(e,A[:,3])[0,1]:.2f}")
    print("by thermal-time fraction (Cycles factor | engine start/grown | start/full | end/grown | end/full), and the share of days with Cycles factor<0.999:")
    for lo in np.arange(0,1.0,0.1):
        k=(A[:,0]>=lo)&(A[:,0]<lo+0.1)
        if k.sum()>200: print(f"  {lo:.1f}-{lo+.1:.1f} n={k.sum():6d}: {A[k,3].mean():.3f} | "+" | ".join(f"{A[k,5+j].mean():.3f}" for j in range(4))+f" | stressed days Cycles {100*(A[k,3]<0.999).mean():.0f}% engine(start/grown) {100*(A[k,5]<0.999).mean():.0f}%")
