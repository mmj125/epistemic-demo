"""Rebuild phase 4 (2026-10-16): per-site daily arrays of Cycles' own N fluxes and the per-layer states that drive them
(NO3/NH4 kg/ha by layer, theta, soil T, drainage), so each engine rate law can be tested one step at a time with Cycles' own states as input.
Usage: python3 nlaw_data.py N_SITES"""
import os,sys,csv,json,numpy as np
sys.path.insert(0,'.')
import run_validation_multisite as m
CY=m.CY
def rd(path):
    rows=list(csv.reader(open(path))); h=rows[0]; body=[r for r in rows[2:] if r and r[0][0]!='#']
    return h,body
def build(site,N):
    d=f'{CY}/output/{site}N{N}/'
    hN,bN=rd(d+'dailyN.csv'); hL,bL=rd(d+'dailySoilLayersCN.csv'); hW,bW=rd(d+'dailyWater.csv'); hE,bE=rd(d+'dailyEnviron.csv')
    n=min(len(bN),len(bL),len(bW),len(bE))
    ix=lambda h,pre:[i for i,x in enumerate(h) if x.startswith(pre)]
    f=lambda b,cols:np.array([[float(r[c]) for c in cols] for r in b[:n]])
    cN=lambda k:hN.index(k)
    out=dict(date=np.array([r[0] for r in bN[:n]]))
    for k in ('profile_soil_NO3','profile_soil_NH4','net_mineralization','nitrification','volatilization','denitrification','NO3_leaching','NH4_leaching','N2O_from_denitrification'):
        out[k]=f(bN,[cN(k)])[:,0]
    thick=f(bL,ix(hL,'thickness.'))[0]; bd=f(bL,ix(hL,'bulk_density.'))[0]
    out['thick']=thick; out['bd']=bd
    out['no3_l']=f(bL,ix(hL,'NO3.'))*bd*thick*10; out['nh4_l']=f(bL,ix(hL,'NH4.'))*bd*thick*10
    out['theta']=f(bW,ix(hW,'soil_moisture_content.')); out['drain']=f(bW,[hW.index('drainage')])[:,0]
    out['tsoil']=f(bE,ix(hE,'soil_temperature.')); out['tair']=f(bE,[hE.index('average_air_temperature')])[:,0]
    return out
if __name__=="__main__":
    S=json.load(open('sitesets/fresh94.json')); ks=sorted(S); n=int(sys.argv[1]); ks=[ks[i] for i in range(0,len(ks),max(1,len(ks)//n))][:n]
    for k in ks:
        lat,lon=S[k]; soil,_,name=m.fd.resolve_field_soil(lat,lon)
        sat=[];fc=[];pw=[]
        for l in soil:
            h=m.saxton_rawls(l['sand'],l['clay'],l['soc']*m.OM_FROM_SOC); sat.append(h['sat']);fc.append(h['fc']);pw.append(h['pwp'])
        for N in (0,150):
            if not os.path.exists(f'{CY}/output/{k}N{N}/dailyN.csv'): continue
            o=build(k,N); np.savez_compressed(f'/tmp/w/nlaw/{k}N{N}.npz',sat=sat,fc=fc,pwp=pw,clay=[l['clay'] for l in soil],soc=[l['soc'] for l in soil],**o)
        print(k,name[:14],len(soil),'layers',flush=True)
