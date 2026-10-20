"""Classifies every module-level constant of cycles_engine_validate.py by provenance (2026-10-20). Classes:
 DIAG  diagnostic hook, no model effect;   OFF  option switched off by default (dead unless enabled);
 DOC   documented in the paper, SI, crop file, guide, or a standard published reference;
 C     constant fitted or measured on Cycles' own output (form from the paper or literature);
 D     whole law identified from Cycles' output (form and constants);
 ENG   engine design choice or numerical setting, not a fit;
 LEG   superseded legacy constant (a newer path overrides it; verify before deleting).
Usage: python3 inventory_2026_10_20.py   prints counts and the members of each class."""
import ast,re,collections
src=open('cycles_engine_validate.py').read(); tree=ast.parse(src)
rows={}
for n in tree.body:
    if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name):
        nm=n.targets[0].id
        if re.fullmatch(r"_?[A-Z][A-Z0-9_]*",nm): rows[nm]=ast.get_source_segment(src,n.value)
DIAG=re.compile(r"_?(DIAG|CFORCE|FORCE_SERIES|NPOOL_FORCE|NLAYER_FORCE|THETA_FORCE|N_SOLVE|N_UNMET|FORCE_CUR|CUR_SIXPOOL|SUBDAY_REL1)")
LEG={"CN_RATIO_SOM","NITRIF_RMAX","NITRIF_K","NITRIF_T0","NITRIF_FE","DENITRIF_K0","DENITRIF_EXPONENT","DENITRIF_RELSAT_EXPONENT","DENITRIF_K_REL","DENITRIF_THRESHOLD_FORM","DENITRIF_THR_K","DENITRIF_THR_REL","DENITRIF_THR_POW","DENITRIF_THR_TEXP","DENITRIF_LAYER1_ONLY","ROTHC_WEATHER_FACTOR_NORM","BACKGROUND_N_KG_HA_DAY","SIXPOOL_N_LIMIT","SIXPOOL_NLIM_MIN","SIXPOOL_NLIM_CENTER","SIXPOOL_NLIM_WIDTH","FE_TEMP_POW","SIXPOOL_KM","SIXPOOL_EPS_C_KM_PRODUCT","DEFAULT_CANOPY_SHAPE","CORN_CANOPY_SHAPE","NET_GROWTH_FRACTION","CANOPY_EIX_FORCE","SURFACE_AIRDRY_FRAC","VOLATILIZATION_RATE_NH4_CAP","VOLATILIZATION_THETA_DEFAULT","SIXPOOL_N_POT_MULT_RES","SIXPOOL_N_HALF_RES_MULT","N_STRESS_FLOOR_RATIO","SIXPOOL_ML_FD_P","SIXPOOL_ML_FD_R0","SIXPOOL_ML_FD_CAP"}
DOC={"OM_FROM_SOC","REW_DEFAULT_MM","CROPSYST_AIRDRY_FRAC","FORCE_CROPSYST_EVAP","LEAF_WATER_POTENTIAL_AT_FC","CROP_WATER_POTENTIAL_K_SEC_PER_DAY","CARBON_FRACTION_DM","NH3_FRAC_SYNTHETIC","NH3_FRAC_MANURE","NCRIT_FLOOR_MGHA","VPD_POW","VPD_D0","SIXPOOL_EPS_C","SIXPOOL_FA","IMMOB_FROM_NO3","N_SIMULTANEOUS","VPD_FAO56","WINTER_PHENOLOGY","MANURE_SOURCES","MINERAL_SOURCES","TILLAGE_IMPLEMENTS","CO2_PPM_BY_YEAR","CANOPY_SHAPE_FORCE","ROOT_TRI_POW","N_AG_FRACTION_UNUSED"}
D=re.compile(r"(NITRIF_RATIO|DENITRIF_RESP|DENITRIF_MM|N2O_|VOLATILIZATION_RATE_[ABCD]|EVAP_LAW_(CYCLES|PARAMS)|RESIDUE_(COVER|RAIN)|SNOW_(MODEL|RAIN|MELT)|SOLUTE_VOL_SAT|VPD_CYCLES_EXACT|VPD_FLOOR_KPA|VPD_DAYTIME_ALPHA|SIXPOOL_FE_|FE_TEMP_CYCLES|SIXPOOL_ML_TEMP_TABLE|SIXPOOL_ML_FD_SI|SIXPOOL_ML_HUM_CLAY)")
C=re.compile(r"(SIXPOOL_(KS|KRA|K_RTZ|KRM|ML_|N_|DEPTH|CN_|TOPSOIL)|ROOT_C_|TTF50|N_STRESS_|N_AG_FRACTION|CANOPY_(N_|WATER_POW|FAITHFUL)|C1_|HEAT_A|WUE_CO2_EXP|N_DEMAND_SCALE|N_UPTAKE_FLOOR|INITIAL_MOISTURE|PSI_E_FROM|KHE_SCALE|CRA_MATURATION|CO2_REF_PPM|RESIDUE_COVER_BIOMASS|EVAP_ZONE|SOIL_EVAP_SCALE|ROOT_DENSITY_DECAY|ROOT_TTF_FULL)")
cls=collections.defaultdict(list)
for nm,v in rows.items():
    off = v in ("False","None","0.0","0","()") and not DIAG.match(nm)
    if DIAG.match(nm): k="DIAG"
    elif nm in LEG: k="LEG"
    elif off: k="OFF"
    elif nm in DOC: k="DOC"
    elif D.match(nm) or D.search(nm): k="D"
    elif C.match(nm) or C.search(nm): k="C"
    else: k="ENG"
    cls[k].append(nm)
for k in ("DOC","ENG","C","D","LEG","OFF","DIAG"): print(f"{k:5s} {len(cls[k]):3d}  "+", ".join(cls[k]) if k in ("ENG","D","C","DOC") else f"{k:5s} {len(cls[k]):3d}")
print("total",len(rows))
