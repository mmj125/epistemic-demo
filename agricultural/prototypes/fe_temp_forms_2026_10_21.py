import numpy as np
from scipy.optimize import least_squares
pts=np.array([(0.0, 0.0), (1.5, 0.026), (3.5, 0.045), (5.5, 0.077), (7.5, 0.120), (9.5, 0.170), (11.5, 0.231), (13.5, 0.303), (15.5, 0.385), (17.5, 0.468), (19.5, 0.554), (21.5, 0.641), (23.5, 0.731), (25.5, 0.810), (27.5, 0.877), (31.0, 1.0)])
T,y=pts[:,0],pts[:,1]
def fit(nm,f,p0):
    r=least_squares(lambda p:f(p,T)-y,p0,max_nfev=2000); e=f(r.x,T)-y; print(f" {nm:42s} max abs err {np.abs(e).max():.3f} rms {np.sqrt((e**2).mean()):.3f} p {np.round(r.x,3)}"); return r.x
fit("(T/To)^a",lambda p,t:np.clip(t/p[0],0,None)**p[1],[31,1.4])
fit("((T-Tb)/(To-Tb))^a",lambda p,t:np.clip((t-p[2])/(p[0]-p[2]),0,None)**p[1],[31,1.2,0.5])
fit("quadratic aT+bT^2",lambda p,t:p[0]*t+p[1]*t*t,[0.01,0.001])
fit("logistic",lambda p,t:1/(1+np.exp(-p[0]*(t-p[1]))),[0.15,18])
fit("Q10 exp ((T-31)/10 lnQ)",lambda p,t:np.exp(p[0]*(t-31)),[0.08])
fit("Arrhenius exp(-E(1/(T+273)-1/304))",lambda p,t:np.exp(-p[0]*(1/(t+273.15)-1/304.15)),[5000])
fit("Campbell (T+4) form To free",lambda p,t:np.clip((2*(t+4)**2*(p[0]+4)**2-(t+4)**4)/(p[0]+4)**4,0,None),[35])
fit("Campbell (T+c) form, c, To free",lambda p,t:np.clip((2*(t+p[1])**2*(p[0]+p[1])**2-(t+p[1])**4)/(p[0]+p[1])**4,0,None),[35,4])
fit("Eq11 shape (0.0105T+0.00095T^2 /0.032T-0.12)",lambda p,t:p[0]*np.where(t<10,0.0105*t+0.00095*t*t,0.032*t-0.12),[1.0])
