"""Late-season growth efficiency fitted to Mead observed above-ground biomass and grain (2026-10-26). Engine with tower-adjusted weather, planting days inferred from the early LAI, corn years, current defaults (senescence law on). Grid over LATE_RUE_X0 and LATE_RUE_F.
Loss: squared relative error of harvest above-ground total (11 site-years) and grain (6 site-years), plus relative error of the observed biomass series in August and September. Leave one site out. Usage: python3 mead_late_rue_2026_10_26.py"""
import os,sys,json,math,copy,datetime
sys.path.insert(0,'.')
import numpy as np, mead_score_2026_10_23 as M, rhizo_engine as E
E.TTF50_SHOOT_PARTITION=float(os.environ.get('T50','0.42')); print('TTf50',E.TTF50_SHOOT_PARTITION)
SH=[121,124,127,130,133,136,139,142]; C_FRAC=0.438; DATA={}
for s in ("Ne1","Ne2","Ne3"):
    soil,b,pl,lat,lon,wx,CW,CH,CYld,T=M._cache(s,"toweradj"); obs={}
    for l in b["lai"]:
        d=l["LAI_DATE"]; iso=f"{d[:4]}-{d[4:6]}-{d[6:]}"; y=int(d[:4])
        if y in pl and pl[y]["crop"]=="corn" and not pl[y].get("documented_plant"): obs.setdefault(y,[]).append((iso,1-math.exp(-0.55*float(l["LAI_TOT"])),datetime.date.fromisoformat(iso).timetuple().tm_yday))
    runs={}
    for sh in SH:
        p2=copy.deepcopy(pl)
        for y,v in p2.items():
            if v["crop"]=="corn" and not v.get("documented_plant"): v["plant"]=sh
        res=M.engine_run(s,soil,p2,lat,wx); ED,_=M.engine_parse(res,soil); runs[sh]=ED
    best={}
    for y,L in obs.items():
        early=[x for x in L if x[2]<195 and all(x[0] in runs[sh] for sh in SH)]
        if len(early)>=3: best[y]=min(SH,key=lambda sh:np.sqrt(np.mean([(runs[sh][x[0]]["fi"]-x[1])**2 for x in early])))
    p3=copy.deepcopy(pl)
    for y,sh in best.items(): p3[y]["plant"]=sh
    prod={}
    for p in b["production"]:
        y=int(p["AG_PROD_DATE_START"][:4]); prod.setdefault(y,{})[p["AG_PROD_CROP_ORGAN"]]=float(p["AG_PROD_CROP"])/C_FRAC/100.0
    ob={}
    for x in b["biomass"]:
        if x["AG_BIOMASS_CROP_ORGAN"]=="Foliage":
            d=x["AG_BIOMASS_DATE"]; y=int(d[:4])
            if y in best and int(d[4:6])>=7: ob[f"{d[:4]}-{d[4:6]}-{d[6:]}"]=float(x["AG_BIOMASS_CROP"])/C_FRAC/100.0
    DATA[s]=(soil,p3,lat,wx,best,prod,ob); print(s,"years",sorted(best),flush=True)
GRID=[(1.0,1.0)]+[(x0,f) for x0 in (0.5,0.6,0.7,0.8) for f in (0.8,0.6,0.4,0.2,0.0)]
EXTRA=(0.7,0.6)
R={}
for s,(soil,p3,lat,wx,best,prod,ob) in DATA.items():
    for g in GRID:
        E.LATE_RUE_X0,E.LATE_RUE_F=g
        try: res=M.engine_run(s,soil,p3,lat,wx)
        finally: E.LATE_RUE_X0,E.LATE_RUE_F=0.7,1.0
        ED,EY=M.engine_parse(res,soil); ag=[];gr=[];bio=[]
        for y in best:
            if y in EY and y in prod:
                if not np.isnan(prod[y].get("Total",np.nan)): ag.append((prod[y]["Total"],EY[y]["ag"]))
                if not np.isnan(prod[y].get("Fruits",np.nan)): gr.append((prod[y]["Fruits"],EY[y]["grain"]))
        for iso,v in ob.items():
            if iso in ED: bio.append((v,ED[iso]["ag"]))
        R[(s,g)]=(np.array(ag),np.array(gr),np.array(bio))
def loss(sites,g):
    t=[];
    for s in sites:
        ag,gr,bio=R[(s,g)]
        if len(ag): t+=list((ag[:,1]/ag[:,0]-1)**2)
        if len(gr): t+=list((gr[:,1]/gr[:,0]-1)**2)
        if len(bio): t+=list(0.5*(bio[:,1]/bio[:,0]-1)**2)
    return float(np.mean(t))
SITES=list(DATA)
print("grid: loss (pooled) rows x0, columns F 1.0(none) 0.8 0.6 0.4 0.2 0.0")
print(" none",round(loss(SITES,(1.0,1.0)),4))
for x0 in (0.5,0.6,0.7,0.8): print(f" {x0}",[round(loss(SITES,(x0,f)),4) for f in (0.8,0.6,0.4,0.2,0.0)])
bestg=min(GRID,key=lambda g:loss(SITES,g)); print("best pooled",bestg)
for s in SITES:
    others=[o for o in SITES if o!=s]; g=min(GRID,key=lambda g:loss(others,g))
    for nm,gg in (("baseline",(1.0,1.0)),("LOSO",g),("pooled best",bestg)):
        ag,gr,bio=R[(s,gg)]
        print(f" {s} {nm:11s} {gg}: harvest above-ground engine/obs {ag[:,1].sum()/ag[:,0].sum():.3f}  grain {gr[:,1].sum()/gr[:,0].sum() if len(gr) else float('nan'):.3f}  Aug-Sep biomass series {bio[:,1].mean()/bio[:,0].mean():.3f}")

for gg in ((0.7,0.6),(0.7,0.4)):
    print("setting",gg,{s_:(round(R[(s_,gg)][0][:,1].sum()/R[(s_,gg)][0][:,0].sum(),3),round(R[(s_,gg)][1][:,1].sum()/R[(s_,gg)][1][:,0].sum(),3) if len(R[(s_,gg)][1]) else None) for s_ in SITES},"pooled loss",round(loss(SITES,gg),4))
