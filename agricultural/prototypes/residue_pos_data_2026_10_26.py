"""Cycles' standing and flat residue carbon (dailySoilLayersCN.csv), layer-1 water, and the engine's weather for 10 fresh94 sites, continuous no-till corn N=150 (2026-10-26). Saves /tmp/w/respos.json {site: {...daily lists...}}."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import run_validation_multisite as m
F=json.load(open('sitesets/fresh94.json')); ks=sorted(F)[::9][:10]; out={}
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
for site in ks:
    lat,lon=F[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    C=rd(d+"dailySoilLayersCN.csv"); W=rd(d+"dailyWater.csv"); R=rd(d+"dailyResidue.csv"); shutil.rmtree(d,ignore_errors=True)
    o=dict(date=[],S=[],Fl=[],th1=[],tx=[],tn=[],pp=[],cov=[],ag=[],comp1=[])
    for c,w,r in zip(C,W,R):
        dt=datetime.date.fromisoformat(c['date']); day=wx[dt.year][dt.timetuple().tm_yday] if dt.year in wx and dt.timetuple().tm_yday in wx[dt.year] else None
        if day is None: continue
        o['date'].append(c['date']); o['S'].append(float(c['standing_residue_carbon'])); o['Fl'].append(float(c['flat_residue_carbon'])); o['th1'].append(float(w['soil_moisture_content.1']))
        o['tx'].append(day['tx']); o['tn'].append(day['tn']); o['pp'].append(day['pp']); o['cov'].append(float(r['radiation_interception'])); o['ag'].append(float(r['aboveground_residue_biomass'])); o['comp1'].append(float(c['composite_factor.1']))
    out[site]=o; print(site,len(o['date']))
json.dump(out,open('/tmp/w/respos.json','w'))
