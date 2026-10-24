"""Annual nitrogen budget by window, engine vs Cycles v1.5.20 (2026-10-14), python3 annual_budget.py [N].
Windows (same dates for both models, set by the ENGINE's planting day and last crop day): WINTER Dec31->plant, SEASON plant->last crop day, FALL last crop day->Dec31.
Terms kg N/ha: pool at the start, net mineralization, crop uptake (season), leaching, denitrification, volatilization, pool at the end, closure = start+min-uptake-losses-end."""
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
        _p=nstate['n_nh4']+(sum(nstate['no3_layers']) if nstate.get('no3_layers') else nstate['n_no3'])
        fl.append((ywin['i'],rows[0]['doy'] if rows else None,out,_p))
        return out
    E.sixpool_ml_step=wmin;E.run_fallow_n_window=wfl
    try:r=m.engine(site,wx,soil,cl,N,'leadin')
    finally:E.sixpool_ml_step=o_min;E.run_fallow_n_window=o_fl
    D={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyN.csv')):
        if x['date'][0]!='#':D[x['date']]=x
    TN={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
        if x['date'][0]!='#' and x['biomass']!='-999':TN[x['date'][:4]]=max(TN.get(x['date'][:4],0.0),float(x['total_nitrogen']))
    pool=lambda d:float(D[d]['profile_soil_NO3'])+float(D[d]['profile_soil_NH4'])
    ys=sorted(r);res=[]
    for i,y in enumerate(ys):
        if i==0 or (y-1) not in r:continue
        h=r[y].get('history');prev=r[y-1].get('end_n_state');fin=r[y].get('final_n_state');end=r[y].get('end_n_state')
        if not h or not prev or not fin or not end:continue
        pd=r[y]['plant_doy'];ld=r[y].get('last_doy') or 299
        S=lambda s:s['n_nh4']+(sum(s['no3_layers']) if s.get('no3_layers') else s['n_no3'])
        fw=[t for t in fl if t[0]==i and t[1]==1];fb=[t for t in fl if t[0]==i and t[1]!=1];fbp=[t for t in fl if t[0]==i-1 and t[1]!=1]
        if not fw or not fb or not fbp:continue
        e_dec_prev,e_plant,e_harv,e_dec=fbp[0][3],h[0]['n_pool'],h[-1]['n_pool'],fb[0][3]
        mn=lambda a,b:sum(v for (yi,d,v) in mins if yi==i and a<=d<=b)
        wl=fw[0][2] if fw else (0,0,0);fa=fb[0][2] if fb else (0,0,0)
        tot_l=r[y]['n_leached_kg_ha'];tot_d=r[y]['n_denitrified_kg_ha'];tot_v=r[y]['n_volatilized_pool_kg_ha']
        s_l=tot_l-r[y].get('fallow_n_leached',0.0);s_d=tot_d-r[y].get('fallow_n_denitrified',0.0);s_v=tot_v-r[y].get('fallow_n_volatilized',0.0)
        jan=lambda doy:datetime.date(y,1,1)+datetime.timedelta(doy-1)
        dD=datetime.date(y-1,12,31);dP=jan(pd-1);dH=jan(ld);dE=datetime.date(y,12,31)
        if any(d.isoformat() not in D for d in (dD,dP,dH,dE)):continue
        def cyc(k,a,b):
            return sum(float(D[(a+datetime.timedelta(j)).isoformat()][k]) for j in range(1,(b-a).days+1) if (a+datetime.timedelta(j)).isoformat() in D)
        cl_=lambda a,b:cyc('NO3_leaching',a,b)+cyc('NH4_leaching',a,b)
        up=TN.get(str(y),np.nan)
        res.append(dict(y=y,
          W=dict(e=[e_dec_prev,mn(0,pd-1),0,wl[0],wl[1],wl[2],e_plant],c=[pool(dD.isoformat()),cyc('net_mineralization',dD,dP),0,cl_(dD,dP),cyc('denitrification',dD,dP),cyc('volatilization',dD,dP),pool(dP.isoformat())]),
          S=dict(e=[e_plant,mn(pd,ld),r[y].get('n_uptake_kg_ha',np.nan),s_l,s_d,s_v,e_harv],c=[pool(dP.isoformat()),cyc('net_mineralization',dP,dH),up,cl_(dP,dH),cyc('denitrification',dP,dH),cyc('volatilization',dP,dH),pool(dH.isoformat())]),
          F=dict(e=[e_harv,mn(ld+1,400),0,fa[0],fa[1],fa[2],e_dec],c=[pool(dH.isoformat()),cyc('net_mineralization',dH,dE),0,cl_(dH,dE),cyc('denitrification',dH,dE),cyc('volatilization',dH,dE),pool(dE.isoformat())])))
    return site,res
if __name__=="__main__":
    with Pool(4) as p: out=p.map(one,list(ALL))
    json.dump(out,open(f'/tmp/w/annual_budget_N{N}.json','w'),default=float)
    names=['start','netmin','uptake','leach','denit','volat','end']
    for wk,wn in (('W','WINTER Dec31->plant'),('S','SEASON plant->last day'),('F','FALL last day->Dec31')):
        diffs=[];rows=[]
        for s,res in out:
            if not res:continue
            E_=np.array([r[wk]['e'] for r in res],float);C_=np.array([r[wk]['c'] for r in res],float)
            me,mc=np.nanmean(E_,0),np.nanmean(C_,0);diffs.append(me-mc)
            ce=me[0]+me[1]-me[2]-me[3]-me[4]-me[5]-me[6];cc=mc[0]+mc[1]-mc[2]-mc[3]-mc[4]-mc[5]-mc[6]
            rows.append((s,me,mc,ce,cc))
        A=np.array(diffs)
        print('\n== %s  (engine minus Cycles, mean over sites; and mean |.|)'%wn)
        print('   '+'  '.join('%s %+.1f(|%.1f|)'%(n,A[:,i].mean(),np.abs(A[:,i]).mean()) for i,n in enumerate(names)))
        print('   closure engine %+.1f   closure Cycles %+.1f  (start+min-uptake-losses-end)'%(np.mean([r[3] for r in rows]),np.mean([r[4] for r in rows])))
