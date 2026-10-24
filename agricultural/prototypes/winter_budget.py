"""Winter nitrogen budget, engine vs Cycles v1.5.20 (2026-10-14), N = 0 by default (python3 winter_budget.py [N]).
Window per year: December 31 of the previous year to the day before the ENGINE's planting day (same dates for both models).
Terms (kg N/ha): start pool, net mineralization, leaching, denitrification, volatilization, end pool (planting-day pool)."""
import sys,os,csv,datetime,json,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
import rhizo_engine as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
N=int(sys.argv[1]) if len(sys.argv)>1 else 0
orig=m.simulate_continuous
def sc(*a,**k):
    k['record_history']=True;return orig(*a,**k)
m.simulate_continuous=sc
def one(site):
    lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    mins=[];state={'yr':-1,'last':400}
    o_min=E.sixpool_ml_step
    def wmin(st,tmean,layers,*a,**k):
        r=o_min(st,tmean,layers,*a,**k)
        f=sys._getframe(1);doy=None
        while f is not None and doy is None:
            ww=f.f_locals.get('w')
            if isinstance(ww,dict) and 'doy' in ww:doy=ww['doy']
            f=f.f_back
        if doy is not None:
            if doy<state['last']-100:state['yr']+=1
            state['last']=doy;mins.append((state['yr'],doy,r))
        return r
    fl=[];ywin={'i':-1}
    o_fl=E.run_fallow_n_window
    def wfl(layers,rows,nstate,*a,**k):
        out=o_fl(layers,rows,nstate,*a,**k)
        if rows and rows[0]['doy']==1:ywin['i']+=1
        fl.append((ywin['i'],rows[0]['doy'] if rows else None,rows[-1]['doy'] if rows else None,out))
        return out
    E.sixpool_ml_step=wmin;E.run_fallow_n_window=wfl
    try:r=m.engine(site,wx,soil,cl,N,'leadin')
    finally:E.sixpool_ml_step=o_min;E.run_fallow_n_window=o_fl
    D={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyN.csv')):
        if x['date'][0]=='#':continue
        D[x['date']]=x
    ys=sorted(r);first=ys[0];res=[]
    for i,y in enumerate(ys):
        if i==0 or y not in r or (y-1) not in r:continue
        h=r[y].get('history');prev=r[y-1].get('end_n_state')
        if not h or not prev:continue
        pd=r[y]['plant_doy']
        e_start=prev['n_nh4']+(sum(prev['no3_layers']) if prev.get('no3_layers') else prev['n_no3'])
        e_end=h[0]['n_pool']
        e_min=sum(v for (yi,d,v) in mins if yi==i and d<pd)
        w=[t for t in fl if t[0]==i and t[1]==1]
        e_lch,e_dn,e_vl=(w[0][3] if w else (None,None,None))
        d0=datetime.date(y-1,12,31);d1=datetime.date(y,1,1)+datetime.timedelta(pd-2)
        def cyc(k):return sum(float(D[(d0+datetime.timedelta(j)).isoformat()][k]) for j in range(1,(d1-d0).days+1) if (d0+datetime.timedelta(j)).isoformat() in D)
        ds=d0.isoformat();de=d1.isoformat()
        if ds not in D or de not in D:continue
        c_start=float(D[ds]['profile_soil_NO3'])+float(D[ds]['profile_soil_NH4']);c_end=float(D[de]['profile_soil_NO3'])+float(D[de]['profile_soil_NH4'])
        res.append(dict(y=y,e=[e_start,e_min,e_lch,e_dn,e_vl,e_end],c=[c_start,cyc('net_mineralization'),cyc('NO3_leaching')+cyc('NH4_leaching'),cyc('denitrification'),cyc('volatilization'),c_end]))
    return site,res
if __name__=="__main__":
    with Pool(4) as p: out=p.map(one,list(ALL))
    json.dump(out,open(f'/tmp/w/winter_budget_N{N}.json','w'))
    names=['start pool','net min','leach','denit','volat','end pool']
    print('N=%d, kg N/ha, mean over years. Engine / Cycles for each term (window = Dec31 to engine planting)'%N)
    print('%-13s'%'site'+' '.join('%-17s'%n for n in names)+'  closure(engine) closure(Cycles)')
    agg=[]
    for s,res in out:
        if not res:continue
        E_=np.array([[v if v is not None else np.nan for v in r['e']] for r in res]);C_=np.array([r['c'] for r in res])
        me,mc=np.nanmean(E_,0),C_.mean(0)
        ce=me[0]+me[1]-me[2]-me[3]-me[4]-me[5];cc=mc[0]+mc[1]-mc[2]-mc[3]-mc[4]-mc[5]
        print('%-13s'%s+' '.join('%6.1f/%-6.1f     '%(me[i],mc[i]) for i in range(6))+' %+7.1f %+7.1f'%(ce,cc))
        agg.append((me,mc))
    A=np.array([a[0]-a[1] for a in agg])
    print('\nmean engine-minus-Cycles over sites:',' '.join('%s %+.1f'%(n,v) for n,v in zip(names,A.mean(0))))
    print('mean |engine-minus-Cycles|          :',' '.join('%s %.1f'%(n,v) for n,v in zip(names,np.abs(A).mean(0))))
    print('corr across sites of end-pool error with each term error:',' '.join('%s %+.2f'%(n,np.corrcoef(A[:,5],A[:,i])[0,1]) for i,n in enumerate(names[:5])))
