"""State audit against Cycles' daily output (2026-10-27): for NS sites (corn, N=150, continuous chain), monthly means of Cycles and the engine for soil temperature, layer water content,
the decomposition environmental factor (Cycles' composite_factor, engine fE), nitrate and ammonium by layer, surface residue carbon and total respired carbon.
Usage: NS=8 [CROPSEL=corn] python3 state_audit_2026_10_27.py   (engine settings from the module defaults and ENGINE_OVR like the harness)"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; os.environ["CROPSEL"]=os.environ.get("CROPSEL","corn"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json')); NS=int(os.environ.get("NS","8")); ks=sorted(S)[::max(1,94//NS)][:NS]
def rd(path): return [r for r in csv.DictReader(open(path)) if r['date'][0]!='#']
def ym(s): d=datetime.date.fromisoformat(s); return d.year,d.timetuple().tm_yday,d.month
def one(site):
    lat,lon=S[site]; N=150
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    Ev=rd(d+"dailyEnviron.csv"); Wt=rd(d+"dailyWater.csv"); CN=rd(d+"dailySoilLayersCN.csv"); SC=rd(d+"dailySoilC.csv"); shutil.rmtree(d,ignore_errors=True)
    nl=len(soil); bd=[E.sixpool_bulk_density(m.saxton_rawls(l['sand'],l['clay'],l['soc']*m.OM_FROM_SOC)['sat']) for l in soil]
    cy={}
    for i in range(min(len(Ev),len(Wt),len(CN),len(SC))):
        y,dd,mo=ym(Ev[i]['date'])
        cy[(y,dd)]=dict(mo=mo,t=[float(Ev[i][f'soil_temperature.{j+1}']) for j in range(nl)],th=[float(Wt[i][f'soil_moisture_content.{j+1}']) for j in range(nl)],
            fe=[float(CN[i][f'composite_factor.{j+1}']) for j in range(nl)],no3=[float(CN[i][f'NO3.{j+1}']) for j in range(nl)],nh4=[float(CN[i][f'NH4.{j+1}']) for j in range(nl)],
            res=float(CN[i]['standing_residue_carbon'])+float(CN[i]['flat_residue_carbon']),resall=float(CN[i]['standing_residue_carbon'])+float(CN[i]['flat_residue_carbon'])+sum(float(CN[i][f'residue_carbon.{j+1}']) for j in range(nl)),resp=float(SC[i]['residue_respired_carbon'])+float(SC[i]['soil_organic_matter_respired_carbon']))
    E.DIAG_THETA=[]; E.DIAG_FE=[]; E.DIAG_CPOOL=[]; E.DIAG_NO3=[]; E.DIAG_DENIT=[]
    m.engine(site,wx,soil,cl,N,'leadin')
    th={(y,dd):v for (y,dd,v) in E.DIAG_THETA if y is not None}
    fe={}
    for (y,dd,i,t,rw,f) in E.DIAG_FE:
        if y is not None: fe.setdefault((y,dd),{})[i]=(t,f)
    cp={(y,dd):c for (y,dd,cs,cm,cr,c) in E.DIAG_CPOOL if y is not None}; cpa={(y,dd):c+sum(sum(x) if hasattr(x,'__iter__') else x for x in cr) for (y,dd,cs,cm,cr,c) in E.DIAG_CPOOL if y is not None}
    no3={(y,dd):v for (y,dd,v) in E.DIAG_NO3 if y is not None}
    rs={(t[0],t[1]):t[4] for t in E.DIAG_DENIT if t[0] is not None}
    for nm in ("DIAG_THETA","DIAG_FE","DIAG_CPOOL","DIAG_NO3","DIAG_DENIT"): setattr(E,nm,None)
    mass=[bd[j]*soil[j]['thick']*10.0 for j in range(nl)]   # kg N/ha per mg/kg
    rows=[]
    for k,c in cy.items():
        if k[0]<1986 or k not in th or k not in fe: continue
        e=dict(th=th[k],t=[fe[k][j][0] for j in range(nl)],fe=[fe[k][j][1] for j in range(nl)],res=cp.get(k,np.nan),resall=cpa.get(k,np.nan),resp=rs.get(k,np.nan),no3=[no3[k][j]/mass[j] for j in range(nl)] if k in no3 else [np.nan]*nl)
        pad=lambda v:(list(v)+[np.nan]*6)[:6]
        for _d in (c,e):
            for _k in ('t','th','fe','no3','nh4'):
                if _k in _d: _d[_k]=pad(_d[_k])
        rows.append((c['mo'],c,e))
    return rows
def tab(name,rows,fc,fe,fmt="%.3f"):
    print(f"-- {name}: month Cycles / engine")
    out=[]
    for mo in range(1,13):
        a=[fc(c) for (mm,c,e) in rows if mm==mo]; b=[fe(e) for (mm,c,e) in rows if mm==mo]
        out.append((fmt%np.nanmean(a))+"/"+(fmt%np.nanmean(b)))
    print("   "+"  ".join(out))
if __name__=="__main__":
    with Pool(4) as p: R=p.map(one,ks)
    rows=[r for rr in R for r in rr]; nl=6
    for j in range(min(nl,4)): tab(f"soil temperature layer {j+1} (C)",rows,lambda c:c['t'][j],lambda e:e['t'][j],"%.1f")
    for j in range(min(nl,4)): tab(f"water content layer {j+1} (m3/m3)",rows,lambda c:c['th'][j],lambda e:e['th'][j])
    for j in range(min(nl,4)): tab(f"decomposition factor layer {j+1}",rows,lambda c:c['fe'][j],lambda e:e['fe'][j],"%.2f")
    for j in range(min(nl,3)): tab(f"nitrate layer {j+1} (mg/kg)",rows,lambda c:c['no3'][j],lambda e:e['no3'][j],"%.1f")
    tab("surface residue carbon (Cycles standing+flat, engine cra, Mg C/ha)",rows,lambda c:c['res'],lambda e:e['res'],"%.2f")
    tab("all residue C incl. incorporated and roots (Mg C/ha)",rows,lambda c:c['resall'],lambda e:e['resall'],"%.2f")
    tab("total respired carbon (Mg C/ha/d)",rows,lambda c:c['resp'],lambda e:e['resp'],"%.4f")
