"""engine_api.run versus the validation harness, same site, same configuration (2026-10-19). Prints the largest absolute differences; all must be 0.
Usage: python3 check_parity_2026_10_19.py   (about 2 minutes)"""
import os,sys,json
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["FALLN"]="60"; sys.path.insert(0,'.')
import run_validation_multisite as m, run_validation_multisite_wheat as mw, engine_api as api, field_data as fd
SITES={"Iowa":(42.0,-93.6),"Kansas":(37.97,-100.87)}
worst=0.0
for name,(lat,lon) in SITES.items():
    wx,_=fd.resolve_field_weather(lat,lon); soil,_,_=fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
    api.load_site(json.dumps(dict(lat=cl,weather=dict(fields=["pp","tx","tn","solar","rhx","rhn","wind"],years={str(y):{str(d):[r[k] for k in ("pp","tx","tn","solar","rhx","rhn","wind")] for d,r in days.items()} for y,days in wx.items()}),soil=soil)))
    for key,sel in (("corn","corn"),("silage","silage"),("sorghum","sorghum"),("soybean","soy")):
        m.CROPSEL=sel
        for N in ((0,150) if key!="soybean" else (0,)):
            H=m.engine(name,wx,soil,cl,N,"leadin")
            cfg=dict(crop=key,start_year=1980,end_year=2016,n_rate=N,n_timing="planting",fert_source="uan")
            R={r["year"]:r for r in json.loads(api.run(json.dumps(cfg)))["annual"]}
            d=0.0
            for y in H:
                h=H[y]; a=R[y]; g=h["forage"] if key=="silage" else h["grain"]
                leach=h.get("n_leached_kg_ha",0)   # the harness already adds the off-season windows into this field
                d=max(d,abs(g-a["grain"]),abs(h["total"]-a["total"]),abs(leach-a["n_leached"]))
            print(f"{name} {key} N={N}: max abs difference {d:.2e}  ({len(H)} years)"); worst=max(worst,d)
    # cover crop (2026-10-21): corn with cereal rye, API against the chain called directly
    import cycles_engine_validate as E, run_validation_rotation2 as r2
    for N in (0,150):
        crop=dict(m.rv.CORN) if hasattr(m,"rv") else dict(m.cev.CORN); crop["lat_deg"]=cl; crop["make_layers"]=api._make_layers(soil); kw=E.standard_kwargs(soil,N)
        m.CROPSEL="corn"; crop=dict(m.cev.CORN) if False else crop
        rye=dict(r2.WHEAT); rye["lat_deg"]=cl; rye["vern"]=dict(E.WINTER_PHENOLOGY); rye["vern"]["tt_flower_pmax"]=290.0; rye["base_t"]=E.WINTER_PHENOLOGY["base_t"]
        rye.update(hi_x=0.0,hi_o=0.0,calibration_factor=1.0,tr_threshold_t=8.0,residue_n_from_plant=True); rye["make_layers"]=api._make_layers(soil)
        H=E.simulate_continuous(wx,crop,carry_n=True,cover=dict(crop=rye,plant_doy=288,kill_doy=105),**kw)
        cfg=dict(crop="corn",start_year=1980,end_year=2016,n_rate=N,n_timing="planting",fert_source="uan",cover_crop="rye",cover_plant_doy=288,cover_kill_doy=105)
        R={r["year"]:r for r in json.loads(api.run(json.dumps(cfg)))["annual"]}
        d=max(max(abs(H[y]["grain"]-R[y]["grain"]),abs((H[y].get("cover") or {}).get("ag",0)-(R[y]["cover_ag"] or 0))) for y in H if y in R)
        print(f"{name} corn + rye cover N={N}: max abs difference {d:.2e}  ({len(H)} years)"); worst=max(worst,d)
    for N in (0,150):
        H=mw.engine_chain(wx,soil,cl,N,None)
        cfg=dict(crop="wheat",start_year=1980,end_year=2016,n_rate=N,n_timing="planting",fert_source="uan")
        R={r["year"]:r for r in json.loads(api.run(json.dumps(cfg)))["annual"]}
        d=max(max(abs(H[y]["grain"]-R[y]["grain"]),abs(H[y]["total"]-R[y]["total"])) for y in H if y in R)
        print(f"{name} wheat N={N}: max abs difference {d:.2e}  ({len(H)} years)"); worst=max(worst,d)
print("WORST",worst)
