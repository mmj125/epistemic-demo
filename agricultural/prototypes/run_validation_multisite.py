"""Multi-site model-error harness (2026-10-02). Feeds IDENTICAL tile weather + STATSGO2 soil
(field_data.py) to native Cycles v1.4.4 and to this engine at Rock Springs / Iowa / Kansas /
Maryland, continuous corn at N=0 and N=150 (UAN, DOY 110), 1980-2016, so any gap is model error,
not input error. Needs the Cycles binary and input/ files in /tmp/cycles-run (not committed:
licensed). Writes multisite_results.json. Run: python3 run_validation_multisite.py
"""
import os, sys, math, statistics, subprocess, shutil, json
P=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,P)
import field_data as fd
import cycles_engine_validate as cev
from cycles_engine_validate import *
import run_validation as rv
cev.N_DEMAND_SCALE = float(os.environ.get("N_DEMAND_SCALE", cev.N_DEMAND_SCALE))
CY="/tmp/cycles-run"  # a local Cycles v1.4.4 release directory (binary + input/), not committed
SITES=dict(rock_springs=fd.PRESET_SITES["rock_springs"],iowa=fd.PRESET_SITES["iowa"],
           kansas=fd.PRESET_SITES["kansas"],maryland=fd.PRESET_SITES["maryland"],
           # 12 further CONUS sites (added 2026-10-02) so any fit is checked off the original four
           nebraska=(41.0,-98.0),illinois=(40.2,-89.0),ohio=(40.5,-83.5),minnesota=(44.5,-94.5),
           georgia=(32.5,-83.5),texas=(32.0,-97.5),michigan=(43.0,-84.5),carolina=(35.2,-79.0),
           missouri=(38.5,-92.5),indiana=(40.0,-86.5),arkansas=(35.0,-91.5),wisconsin=(44.0,-89.5))
N_LEVELS=[0,150]
def lat_of(lat,lon):
    m=fd.load_manifest(); _,_,k=fd.tile_for_point(lat,lon); d,e=fd.load_tile_bytes(m,k)
    best=min(e["cells"],key=lambda c:math.hypot(c[0]-lat,c[1]-lon)); return best[0]
def write_inputs(site,lat,lon,wx,soil_raw,cell_lat):
    w=open(f"{CY}/input/{site}.weather","w")
    w.write(f"LATITUDE                {cell_lat:.6f}\nALTITUDE                0.000000\nSCREENING_HEIGHT        10.0\n")
    w.write("YEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND\n####    ###     mm      deg C   deg C   MJ/m2   %       %       m/s\n")
    for y in sorted(wx):
        for d in sorted(wx[y]):
            r=wx[y][d]; w.write(f"{y}\t{d}\t{r['pp']:.4f}\t{r['tx']:.2f}\t{r['tn']:.2f}\t{r['solar']:.4f}\t{r['rhx']:.2f}\t{r['rhn']:.2f}\t{r['wind']:.3f}\n")
    w.close()
    s=open(f"{CY}/input/{site}.soil","w")
    s.write(f"CURVE_NUMBER        75\nSLOPE               0\nTOTAL_LAYERS        {len(soil_raw)}\n")
    s.write("LAYER   THICK   CLAY    SAND    SOC     BD      FC      PWP     SON     NO3     NH4     BYP_H   BYP_V\n#       m       %       %       %       Mg/m3   m3/m3   m3/m3   kg/ha   kg/ha   kg/ha   -       -\n")
    for i,l in enumerate(soil_raw,1):
        no3=max(1,round(10*l['thick']/0.05*0.25)) ; s.write(f"{i}\t{l['thick']}\t{l['clay']}\t{l['sand']}\t{l['soc']}\t-999\t-999\t-999\t-999\t{min(no3,10)}\t1\t0.0\t0.00\n")
    s.close()
    base=open(f"{CY}/input/ContinuousCorn.operation").read()
    for N in N_LEVELS:
        op=base
        if N==0:
            a=op.index("FIXED_FERTILIZATION"); b=op.index("TILLAGE"); op=op[:a]+op[b:]
        open(f"{CY}/input/{site}N{N}.operation","w").write(op)
        c=open(f"{CY}/input/ContinuousCorn.ctrl").read().replace("ContinuousCorn.operation",f"{site}N{N}.operation").replace("GenericHagerstown.soil",f"{site}.soil").replace("RockSprings.weather",f"{site}.weather")
        open(f"{CY}/input/{site}N{N}.ctrl","w").write(c)
def run_cycles(site,N):
    subprocess.run(["./Cycles","-b",f"{site}N{N}"],cwd=CY,capture_output=True)
    out=f"{CY}/output/{site}N{N}"; H={}
    for line in open(f"{out}/harvest.txt").readlines()[2:]:
        p=line.split("\t")
        if len(p)<11: continue
        H[int(p[0][:4])]=dict(total=float(p[3]),grain=float(p[5]),plant=p[2],tr=float(p[8]),evap=float(p[9]))
    A={}
    for line in open(f"{out}/annualN.txt").readlines()[2:]:
        p=line.split("\t")
        if len(p)>=12: A[int(p[0])]=dict(leach=float(p[4])+float(p[5]),denit=float(p[8]),volat=float(p[10]))
    return H,A
def doy_of(s):
    import datetime; y,m,d=map(int,s.split("-")); return datetime.date(y,m,d).timetuple().tm_yday
def corr(a,b):
    ma,mb=statistics.mean(a),statistics.mean(b); sa=math.sqrt(sum((x-ma)**2 for x in a)); sb=math.sqrt(sum((x-mb)**2 for x in b))
    return sum((a[i]-ma)*(b[i]-mb) for i in range(len(a)))/(sa*sb) if sa and sb else float('nan')
def engine(site,wx,soil_raw,cell_lat,N,mode,lead_years=2):
    crop=dict(rv.CORN); crop["lat_deg"]=cell_lat
    def ml():
        L=[]
        for l in soil_raw:
            h=saxton_rawls(l["sand"],l["clay"],l["soc"]*OM_FROM_SOC)
            L.append(dict(thick=l["thick"],fc=h["fc"],pwp=h["pwp"],sat=h["sat"],theta=h["pwp"]+INITIAL_MOISTURE_FRACTION*(h["fc"]-h["pwp"]),ksat_mm_day=h["ksat_mm_day"],psi_e_kpa=h["psi_e_kpa"],B=h["B"]))
        return L
    crop["make_layers"]=ml
    kw=dict(n_rate_kg_ha=N,nh4_no3_split=True,model_denitrification=True,model_volatilization=True,
            background_n_model="sixpool",sixpool_topsoil_clay_pct=soil_raw[0]["clay"],
            sixpool_topsoil_soc_pct=soil_raw[0]["soc"],sixpool_profile_raw=soil_raw)
    if N>0: kw["fertilizer_source"]="uan"
    if os.environ.get("NITRATE_LAYERS","1")=="1": kw["nitrate_per_layer"]=True
    res={}
    carry=os.environ.get("CARRY_N","1")=="1"
    lead=int(os.environ.get("LEAD_YEARS",lead_years))
    for y in sorted(wx):
        r=simulate_season_with_leadin(wx,y,crop,lead_years=lead,carry_n=carry,**kw)
        if carry and "fallow_n_leached" in r:   # add the off-season windows so totals are calendar-year like Cycles' annualN.txt
            r["n_leached_kg_ha"]=r.get("n_leached_kg_ha",0.0)+r["fallow_n_leached"]
            r["n_denitrified_kg_ha"]=r.get("n_denitrified_kg_ha",0.0)+r["fallow_n_denitrified"]
            r["n_volatilized_pool_kg_ha"]=r.get("n_volatilized_pool_kg_ha",0.0)+r["fallow_n_volatilized"]
        res[y]=r
    return res
if __name__=="__main__":
    out={}
    for site,(lat,lon) in SITES.items():
        wx,wd=fd.resolve_field_weather(lat,lon); soil,sd,name=fd.resolve_field_soil(lat,lon); cl=lat_of(lat,lon)
        write_inputs(site,lat,lon,wx,soil,cl)
        for N in N_LEVELS:
            H,A=run_cycles(site,N)
            for mode in ["leadin"]:
                E=engine(site,wx,soil,cl,N,mode)
                ys=sorted(set(H)&set(E))
                row={}
                for var,gr,ge in [("grain",lambda y:H[y]["grain"],lambda y:E[y]["grain"]),("total_biomass",lambda y:H[y]["total"],lambda y:E[y]["total"]),
                                  ("plant_doy",lambda y:doy_of(H[y]["plant"]),lambda y:E[y]["plant_doy"])]:
                    a=[gr(y) for y in ys]; b=[ge(y) for y in ys]
                    row[var]=dict(real=statistics.mean(a),model=statistics.mean(b),mae=statistics.mean(abs(x-z) for x,z in zip(a,b)),corr=corr(a,b),n=len(ys))
                if N==150:
                    for k,ek in [("leach","n_leached_kg_ha"),("volat","n_volatilized_pool_kg_ha"),("denit","n_denitrified_kg_ha")]:
                        yy=[y for y in ys if y in A]; a=[A[y][k] for y in yy]; b=[E[y].get(ek,0.0) for y in yy]
                        row[k]=dict(real=statistics.mean(a),model=statistics.mean(b),mae=statistics.mean(abs(x-z) for x,z in zip(a,b)),corr=corr(a,b),n=len(yy))
                out[f"{site}|N{N}|{mode}"]=dict(soil=name,soil_dist=sd,wx_dist=wd,res=row)
                print(site,N,mode,name,{k:(round(v['real'],2),round(v['model'],2),round(v['corr'],2)) for k,v in row.items()},flush=True)
    json.dump(out,open(os.path.join(P,"multisite_results.json"),"w"),indent=1)
