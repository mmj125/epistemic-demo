"""Season N budget, engine vs Cycles (2026-10-16): what the crop takes (uptake), what is left in the mineral pool at harvest, and the in-season losses.
supply = uptake + pool_end + losses is the N that was available to the season; recovery = uptake / supply. 24 fresh sites, N=0 and 150, corn.
Cycles: dailyN.csv summed over planting..harvest, plant N = max total_nitrogen. Engine: result n_uptake, n_remaining, n_leached, n_denitrified, n_volatilized_pool."""
import os,sys,csv,json,shutil,datetime,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        m._run_cycles_uncached(site,N); d=f"{CY}/output/{site}N{N}"
        D={}
        for x in csv.DictReader(open(d+"/dailyN.csv")):
            if x["date"][0]=="#": continue
            D[x["date"]]={k:float(v) for k,v in x.items() if k!="date"}
        PN={}
        for x in csv.DictReader(open(d+"/dailyCornRM.90.csv")):
            if x["date"][0]=="#" or x["total_nitrogen"]=="-999": continue
            y=int(x["date"][:4]); PN[y]=max(PN.get(y,0),float(x["total_nitrogen"]))
        cyc={}
        for x in csv.DictReader(open(d+"/harvest.csv")):
            if x["date"][0]=="#": continue
            hd=x["date"]; pd=x["planting_date"]; y=int(hd[:4])
            if pd not in D or hd not in D or y not in PN: continue
            dd=sorted(k for k in D if pd<=k<=hd)
            loss=sum(D[k]["NO3_leaching"]+D[k]["NH4_leaching"]+D[k]["denitrification"]+D[k]["volatilization"] for k in dd)
            nm=sum(D[k]["net_mineralization"] for k in dd)
            pe=D[hd]["profile_soil_NO3"]+D[hd]["profile_soil_NH4"]; pp=D[pd]["profile_soil_NO3"]+D[pd]["profile_soil_NH4"]
            cyc[y]=dict(bio=float(x["total_biomass"]),up=PN[y],pool_end=pe,loss=loss,pool_plant=pp,netmin=nm)
        shutil.rmtree(d,ignore_errors=True)
        R=m.engine(site,wx,soil,cl,N,"leadin")
        eng={y:dict(bio=r["total"],up=r.get("n_uptake_kg_ha",0),pool_end=r.get("n_remaining_kg_ha",0),
                    loss=r.get("n_leached_kg_ha",0)+r.get("n_denitrified_kg_ha",0)+r.get("n_volatilized_pool_kg_ha",0)) for y,r in R.items() if y in cyc}
        ys=sorted(set(cyc)&set(eng))
        mean=lambda D,k:st.mean(D[y][k] for y in ys)
        out[N]={"cyc":{k:mean(cyc,k) for k in ("up","pool_end","loss","pool_plant","netmin","bio")},"eng":{k:mean(eng,k) for k in ("up","pool_end","loss","bio")},
                "yearly_corr_up":m.corr([cyc[y]["up"] for y in ys],[eng[y]["up"] for y in ys])}
    return site,out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    json.dump(R,open("scorecards/2026-10-16_season_n_budget_24sites.json","w"))
    for N in (0,150):
        print(f"N={N} mean over 24 sites (kg N/ha, planting to harvest)")
        for who in ("cyc","eng"):
            up=st.mean(o[N][who]["up"] for _,o in R); pe=st.mean(o[N][who]["pool_end"] for _,o in R); lo=st.mean(o[N][who]["loss"] for _,o in R)
            bi=st.mean(o[N][who]["bio"] for _,o in R); sup=up+pe+lo; print(f"  {who}: uptake {up:6.1f}  pool at harvest {pe:6.1f}  losses {lo:6.1f}  supply {sup:6.1f}  recovery {up/sup:.2f}  biomass {bi:5.1f} Mg/ha  N per Mg biomass {up/bi:.2f}")
        print("  Cycles pool at planting %.1f  season net mineralization %.1f"%(st.mean(o[N]["cyc"]["pool_plant"] for _,o in R),st.mean(o[N]["cyc"]["netmin"] for _,o in R)))
        print("  site-level corr of uptake (engine vs Cycles): %.2f; mean within-site yearly corr %.2f"%(m.corr([o[N]["cyc"]["up"] for _,o in R],[o[N]["eng"]["up"] for _,o in R]),st.mean(o[N]["yearly_corr_up"] for _,o in R if o[N]["yearly_corr_up"]==o[N]["yearly_corr_up"])))
