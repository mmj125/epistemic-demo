"""Rebuild phase 4: annual respired C and net N mineralization, engine vs Cycles (24 fresh sites, N=150, standard config, continuous run)."""
import os,sys,csv,json,math,statistics as st
os.environ.setdefault('LEAD_YEARS','continuous'); os.environ.setdefault('CARRY_N','1'); os.environ.setdefault('REGIONAL','0')
sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def cyc(site,N=150):
    r=list(csv.reader(open(f'{CY}/output/{site}N{N}/dailySoilC.csv')))[2:]
    n=list(csv.reader(open(f'{CY}/output/{site}N{N}/dailyN.csv')))[2:]
    R={};M={}
    for x in r: R[int(x[0][:4])]=R.get(int(x[0][:4]),0)+float(x[3])+float(x[4])
    for x in n: M[int(x[0][:4])]=M.get(int(x[0][:4]),0)+float(x[6])
    return R,M
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); E.DIAG_RESP=[]
    m.engine(site,wx,soil,cl,150,'leadin'); rec=E.DIAG_RESP; E.DIAG_RESP=None
    er={};en={}
    for y,r,n in rec: er[y]=er.get(y,0)+r; en[y]=en.get(y,0)+n
    cr,cn=cyc(site); ys=[y for y in sorted(cr) if y in er and 1982<=y<=2015]
    f=lambda a,b:(st.mean(a[y] for y in ys),st.mean(b[y] for y in ys))
    def corr(a,b):
        x=[a[y] for y in ys];z=[b[y] for y in ys]; mx,mz=st.mean(x),st.mean(z); sx=math.sqrt(sum((i-mx)**2 for i in x)); sz=math.sqrt(sum((i-mz)**2 for i in z)); return sum((i-mx)*(j-mz) for i,j in zip(x,z))/(sx*sz) if sx*sz else float('nan')
    return site,name,f(er,cr),corr(er,cr),f(en,cn),corr(en,cn)
if __name__=="__main__":
    S=json.load(open('sitesets/fresh94.json')); ks=sorted(S); ks=[ks[i] for i in range(0,len(ks),max(1,len(ks)//24))][:24]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    print('site soil | respired C Mg/ha/yr engine,Cycles,ratio,yearcorr | net N kg/ha/yr engine,Cycles,ratio,yearcorr')
    for s,n,(re,rc),cr,(ne,nc),cn in R: print(f'{s} {n[:12]:12s} resp {re:5.2f} {rc:5.2f} {re/rc:4.2f} {cr:5.2f} | netN {ne:6.0f} {nc:6.0f} {ne/nc if nc else float("nan"):5.2f} {cn:5.2f}')
    rr=[a[2][0]/a[2][1] for a in R]; nr=[a[4][0]/a[4][1] for a in R if a[4][1]>0]
    print('median resp ratio %.2f, median netN ratio %.2f; mean yearcorr resp %.2f netN %.2f'%(st.median(rr),st.median(nr),st.mean(a[3] for a in R),st.mean(a[5] for a in R if a[5]==a[5])))
    json.dump(R,open('/tmp/w/nmin_scorecard.json','w'))
