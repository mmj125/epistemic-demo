"""Equation conformance tests (2026-10-29). Each expected value is computed here from the printed equation (or the Cycles guide formula), independently of the engine, then compared with the engine function. Run: python3 test_equation_conformance_2026_10_29.py"""
import math,sys
sys.path.insert(0,'.')
import rhizo_engine as E, engine_api as A
fails=[]
def chk(name,got,want,tol=1e-9):
    ok=abs(got-want)<=tol*max(1.0,abs(want))
    print(("ok   " if ok else "FAIL ")+f"{name}: engine {got:.6g}, expected {want:.6g}")
    if not ok: fails.append(name)
# SI.1 to SI.4 curve number runoff, standard form (SI prints Win-0.8S; our reading is +0.8S), slope factor of the SI
sf=lambda s:1.1-s/(s+math.exp(3.7+0.02*s))
for win,S,slp in ((50.0,100.0,0.0),(20.0,100.0,3.0),(80.0,60.0,5.0),(10.0,100.0,0.0)):
    Se=S*sf(slp); want=0.0 if win<=0.2*Se else (win-0.2*Se)**2/(win+0.8*Se)
    chk(f"runoff P={win} S={S} slope={slp}",E.runoff_mm(win,S,slp),want)
# SI.5 and SI.6 dry and wet curve numbers (SI.6 with the plus sign); both give 100 at CN 100
for cn in (60.0,75.0,90.0,100.0):
    chk(f"CN dry {cn}",E.cn_dry(cn),cn/(2.3-0.013*cn)); chk(f"CN wet {cn}",E.cn_wet(cn),cn/(0.4+0.006*cn))
chk("CN dry at 100 is 100",E.cn_dry(100.0),100.0); chk("CN wet at 100 is 100",E.cn_wet(100.0),100.0)
# Eq. 6 canopy double sigmoid with the constants of the paper, plateau eix
for t in (0.2,0.5,0.8):
    chk(f"canopy Eq.6 ttf={t}",E.canopy_cover(t,0.95,(6,-20,-16,16)),0.95/(1+math.exp(6-20*t)+math.exp(-16+16*t)))
# SI Eq. 8 shoot fraction: Michaelis-Menten with exponent 4; at ttf = ttf50 it is the midpoint
chk("shoot fraction at TTf50",E.shoot_fraction(0.42,0.45,0.95,0.42),0.70)
chk("shoot fraction at ttf 0.8",E.shoot_fraction(0.8,0.45,0.95,0.42),0.45+0.5/(1+(0.42/0.8)**4))
# Lemaire marginal N demand: d(a/100 W^(1-b))/dW times 100 = a (1-b) W^-b, W in Mg/ha
crop={"n_crit_lemaire":(3.4,0.37)}
for W in (2.0,10.0,25.0): chk(f"Lemaire marginal demand W={W}",E.n_marginal_demand_pct(W,crop),3.4*(1-0.37)*W**-0.37)
# SI.13 saturation factors (printed exponent 6 for fH, fD with 4.5 and 3)
for r in (0.2,0.5,0.9):
    chk(f"fH r={r}",E.sixpool_fh(r,1.0),1-r**6); chk(f"fD r={r}",E.sixpool_fd(r,1.0),1-1/(1+(4.5*r)**3))
# Harvest index slope of the guide: Hk = m (1 - Hmin)/(Hmax - Hmin) with the crop-file values
chk("Hk corn",A._CORN["hi_slope"],(1-0.15)/(0.8-0.15),1e-4); chk("Hk soybean",A._SOYBEAN["hi_slope"],(1-0.15)/(0.4-0.15),1e-4)
print("\nFAILED:",fails if fails else "none"); sys.exit(1 if fails else 0)
