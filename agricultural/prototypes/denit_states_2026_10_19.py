"""Denitrification drivers, engine vs Cycles (2026-10-19): corn, 24 sites, N=150 (and 0/400). Engine: layer-1 relative saturation, profile nitrate, respired C, flux (DIAG_DENIT). Cycles: layer-1 saturation (water content / saturation), profile nitrate, respired carbon (dailySoilC), denitrification.
Reports distributions of each driver and the annual totals."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150,400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    Nn={r['date']:r for r in rd(d+"dailyN.csv")}; W={r['date']:r for r in rd(d+"dailyWater.csv")}; Cc={r['date']:r for r in rd(d+"dailySoilC.csv")}; shutil.rmtree(d,ignore_errors=True)
    sat1=m.saxton_rawls(soil[0]["sand"],soil[0]["clay"],soil[0]["soc"]*m.OM_FROM_SOC)["sat"]
    E.DIAG_DENIT=[]; m.engine(site,wx,soil,cl,N,'leadin'); D=E.DIAG_DENIT; E.DIAG_DENIT=None; last={}
    for y,doy,rel,no3,resp,fl,th,lay in D:
        if y is not None and y>=1982: last[(y,doy)]=(rel,no3,resp,fl,th,lay)
    rows=[]
    for (y,doy),(rel,no3,resp,fl,th,lay) in last.items():
        dt=(datetime.date(y,1,1)+datetime.timedelta(days=doy-1)).isoformat()
        if dt in Nn and dt in W and dt in Cc:
            rows.append((N,rel,float(W[dt]['soil_moisture_content.1'])/sat1,no3,float(Nn[dt]['profile_soil_NO3']),resp*1000,(float(Cc[dt]['soil_organic_matter_respired_carbon'])+float(Cc[dt]['residue_respired_carbon']))*1000,fl,float(Nn[dt]['denitrification']),th,int(dt[5:7]),(lay[0] if len(lay)>0 else 0.0),(lay[1] if len(lay)>1 else 0.0),lay[2] if len(lay)>2 else 0.0,lay[3] if len(lay)>3 else 0.0,sum(lay[4:]) if len(lay)>4 else 0.0))
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150,400)]),[])); np.save('/tmp/w/denit_states.npy',A)
    D2=np.load('/tmp/w/denit_data.npz')['A']
    for n in (0,150,400):
        a=A[A[:,0]==n]; d=D2[D2[:,0]==n]
        print(f'N={n}: nitrate mass by layer (kg N/ha), Cycles | engine: '+' | '.join(f'L{i+1} {d[:,5+4*i].mean():.1f} vs {a[:,11+i].mean():.1f}' for i in range(4))+f' | deeper layers engine {a[:,15].mean():.1f}')
