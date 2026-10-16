"""Cycles daily-state forcing series for the engine diagnostics (copied from swap_test.py so it can be used by the harness without importing it). 2026-10-15."""
import csv,datetime
def force(site,N,keys):
    F={}
    NM={r['date']:float(r['net_mineralization']) for r in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyN.csv')) if r['date'][0]!='#'}
    NN={r['date']:(float(r['profile_soil_NO3']),float(r['profile_soil_NH4'])) for r in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyN.csv')) if r['date'][0]!='#'}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        d=datetime.date.fromisoformat(x['date']);y=d.year;doy=d.timetuple().tm_yday
        f=F.setdefault(y,{'canopy':{},'water':{},'nstress':{},'minn':{},'netmin':{},'wclock':{},'nclock':{}})
        if 'minn' in keys and x['date'] in NN: f['minn'][doy]=NN[x['date']]
        if 'wclock' in keys:
            f['wclock'][doy]=1-float(x['water_stress'])/100;f['nclock'][doy]=1-float(x['nitrogen_stress'])/100
        if 'netmin' in keys and x['date'] in NM: f['netmin'][doy]=NM[x['date']]
        if 'canopy' in keys: f['canopy'][doy]=float(x['radiation_interception'])
        if 'water' in keys: f['water'][doy]=1-float(x['water_stress'])/100
        if 'nstress' in keys: f['nstress'][doy]=1-float(x['nitrogen_stress'])/100
    return F
