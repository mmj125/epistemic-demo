"""Rebuild phase 4: one big daily table (94 fresh sites x N0/150/400) of Cycles' N fluxes and the states/drivers that could explain them,
for law-structure tests. Output /tmp/w/ntable.npz. Usage: python3 nlaw_table.py"""
import os,sys,json,numpy as np,pandas as pd
sys.path.insert(0,'.')
import field_data as fd
from cycles_engine_validate import saxton_rawls, OM_FROM_SOC
CY='/tmp/cycles-run15/output'
COLS=['denit','nit','vol','no3','no3_1','no3_2','nh4','nh4_1','rel1','rel2','relmax','rel1_l1','rel1_l2','rel1_l3','rel1_max5','rel1_mean5','T1','Tair','som','res','hum','drain','drain_l1','pp','infil','et0','vpd','clay','sat1','soc1','Nrate','site','doy','yr','cs_c','leach']
def rd(p): return pd.read_csv(p,skiprows=[1])
def build(site,N,sid,clay,soc1,sat):
    d=f'{CY}/{site}N{N}/'
    n=rd(d+'dailyN.csv'); l=rd(d+'dailySoilLayersCN.csv'); w=rd(d+'dailyWater.csv'); e=rd(d+'dailyEnviron.csv'); c=rd(d+'dailySoilC.csv')
    k=min(len(n),len(l),len(w),len(e),len(c)); n,l,w,e,c=[x.iloc[:k] for x in (n,l,w,e,c)]
    th=w[[x for x in w.columns if x.startswith('soil_moisture_content')]].to_numpy(); L=th.shape[1]
    thick=l[[f'thickness.{i}' for i in range(1,L+1)]].iloc[0].to_numpy(); bd=l[[f'bulk_density.{i}' for i in range(1,L+1)]].iloc[0].to_numpy()
    no3=l[[f'NO3.{i}' for i in range(1,L+1)]].to_numpy()*bd*thick*10; nh4=l[[f'NH4.{i}' for i in range(1,L+1)]].to_numpy()*bd*thick*10
    ts=e[[x for x in e.columns if x.startswith('soil_temperature')]].to_numpy()
    rel=th/np.array(sat[:L])
    r1=rel[:,0]; sh=lambda a,s:np.concatenate([np.repeat(a[:1],s),a[:-s]])
    mx5=pd.Series(r1).rolling(5,min_periods=1).max().to_numpy(); mn5=pd.Series(r1).rolling(5,min_periods=1).mean().to_numpy()
    dr=w['drainage'].to_numpy()
    dates=pd.to_datetime(n['date']); 
    cs=l[[f'soil_organic_carbon.{i}' for i in range(1,L+1)]].sum(axis=1).to_numpy()
    X=np.column_stack([n['denitrification'],n['nitrification'],n['volatilization'],no3.sum(1),no3[:,0],no3[:,1] if L>1 else 0*no3[:,0],nh4.sum(1),nh4[:,0],
        r1,rel[:,1] if L>1 else r1,rel.max(1),sh(r1,1),sh(r1,2),sh(r1,3),mx5,mn5,ts[:,0],e['average_air_temperature'],c['soil_organic_matter_respired_carbon']*1000,c['residue_respired_carbon']*1000,c['humified_carbon']*1000,
        dr,sh(dr,1),e['precipitation'],w['infiltration'],e['reference_evapotranspiration'],e['vapor_pressure_deficit'],np.full(k,clay),np.full(k,sat[0]),np.full(k,soc1),np.full(k,N),np.full(k,sid),dates.dt.dayofyear,dates.dt.year,cs,n['NO3_leaching']+n['NH4_leaching']])
    return X.astype(np.float32)
if __name__=="__main__":
    S=json.load(open('sitesets/fresh94.json')); rows=[]
    for sid,(site,(lat,lon)) in enumerate(sorted(S.items())):
        soil,_,_=fd.resolve_field_soil(lat,lon)
        sat=[saxton_rawls(x['sand'],x['clay'],x['soc']*OM_FROM_SOC)['sat'] for x in soil]
        for N in (0,150,400):
            if os.path.exists(f'{CY}/{site}N{N}/dailyN.csv'): rows.append(build(site,N,sid,soil[0]['clay'],soil[0]['soc'],sat))
        if sid%10==0: print(sid,flush=True)
    T=np.vstack(rows); np.savez_compressed('/tmp/w/ntable.npz',T=T,cols=np.array(COLS)); print(T.shape)
