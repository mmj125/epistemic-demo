"""The one interface between any user interface and the engine (2026-10-19).

The page calls only three functions here: schema() (what controls exist), load_site(json) (weather and soil for the chosen
place) and run(json) (one simulation). The engine file (rhizo_engine.py) can change freely behind them; the page
builds its controls from schema() and its tables from run()'s own column list, so a new engine option is one entry in
SCHEMA below, not a page change.

Configurations here are the ones the scorecard scores: spring crops run as one continuous chain from the first year (the way
Cycles runs 1980 to 2016), with the standard flag set from rhizo_engine.standard_kwargs; winter wheat uses the
fall-to-fall chain with 60 kg N in the fall (run_validation_multisite_wheat.py). check_parity_2026_10_19.py runs this module
against the validation harness and must show identical numbers."""
import copy
import json
import rhizo_engine as E

API_VERSION = 1

# ---- crops (the validated per-crop configurations; sorghum, silage and soybean exactly as the multi-site runner builds them) ----
_CORN = {'root_retained_frac': 0.6, 'n_demand_ref': True, 'n_stress_ag_basis': True, 'n_uptake_rate': 0.03, 'c1_water': True, 'tt_maturity': 1800, 'flowering_tt': 1000, 'base_t': 6, 'opt_t': 28, 'max_t': 46,
         'rue': 2.2, 'wue': 8.7, 'hi_x': 0.8, 'hi_o': 0.15, 'hi_slope': 1.3077, 'fsti': 0.45, 'fstf': 0.95, 'calibration_factor': 1.0, 'canopy_shape': (6, -20, -5.35, 4.1),
         'canopy_shape_faithful': (6.04, -20.51, -14.95, 14.57), 'eix_faithful': 0.951, 'ngf_faithful': 1.0, 'kc': 1.1, 'eix': 1.0, 'tr_min_t': 3.0, 'tr_threshold_t': 15.0, 'lat_deg': 40.6875,
         'n_max_conc': 0.055, 'n_dilution_slope': 0.4, 'legume': False, 'n_min_conc': 0.002, 'depletion_fraction': 0.55, 'tr_max_mm_day': 10, 'root_max_m': 2.0, 'tt_emergence': 65,
         'lwp_stress_onset': -1100, 'lwp_wilting_point': -2000, 'threshold_temp_cold_damage': 3}
_SOYBEAN = {'canopy_shape_faithful': (6.19, -21.11, -15.95, 15.66), 'eix_faithful': 0.924, 'ngf_faithful': 1.0, 'c1_water': True, 'tt_maturity': 2250, 'flowering_tt': 1250, 'base_t': 5, 'opt_t': 28,
            'max_t': 43, 'rue': 1.3, 'wue': 4.5, 'hi_x': 0.4, 'hi_o': 0.15, 'hi_slope': 3.4, 'fsti': 0.45, 'fstf': 0.95, 'kc': 1.0, 'eix': 1.0, 'tr_min_t': 3.0, 'tr_threshold_t': 15.0,
            'lat_deg': 40.6875, 'calibration_factor': 1.0, 'n_max_conc': 0.07, 'n_dilution_slope': 0.4, 'legume': True, 'depletion_fraction': 0.5, 'tr_max_mm_day': 8, 'root_max_m': 1.5,
            'tt_emergence': 70, 'lwp_stress_onset': -1100, 'lwp_wilting_point': -1800, 'threshold_temp_cold_damage': 2}
_SILAGE = {'tt_maturity': 1800, 'flowering_tt': 1000, 'base_t': 6, 'opt_t': 28, 'max_t': 46, 'rue': 2.2, 'wue': 8.7, 'hi_x': 0.8, 'hi_o': 0.15, 'hi_slope': 1.0, 'fsti': 0.45, 'fstf': 0.95, 'kc': 1.1,
           'eix': 1.0, 'tr_min_t': 3.0, 'tr_threshold_t': 15.0, 'lat_deg': 40.6875, 'forage_fraction': 0.95, 'calibration_factor': 1.0, 'depletion_fraction': 0.55,
           'canopy_shape_faithful': (6.05, -20.56, -13.72, 13.33), 'eix_faithful': 0.946, 'ngf_faithful': 1.0, 'canopy_shape': (6, -20, -5.35, 4.1), 'tr_max_mm_day': 10, 'root_max_m': 1.55,
           'tt_emergence': 65, 'n_max_conc': 0.055, 'n_dilution_slope': 0.4, 'legume': False, 'n_min_conc': 0.002, 'lwp_stress_onset': -1100, 'lwp_wilting_point': -2000,
           'threshold_temp_cold_damage': 3, 'n_demand_ref': True, 'n_stress_ag_basis': True, 'n_uptake_rate': 0.03, 'root_retained_frac': 0.6}
_SORGHUM_OVER = dict(tt_maturity=2050, flowering_tt=1300, rue=2.0, wue=9.6, tr_min_t=6, tr_threshold_t=18, kc=1.0, lwp_stress_onset=-1400, lwp_wilting_point=-2300, tr_max_mm_day=9, root_max_m=2.0,
                     tt_emergence=65, threshold_temp_cold_damage=6, canopy_shape_faithful=(6.04, -20.47, -15.52, 15.08), eix_faithful=0.949, ngf_faithful=1.0)
_WHEAT = {'rhizo_rr': 0.6, 'rhizo_root_n_share': 0.082, 'canopy_form': 'H', 'tt_maturity': 1800, 'flowering_tt': 1250, 'base_t': 0, 'opt_t': 20, 'max_t': 35, 'rue': 1.6, 'wue': 6.0, 'hi_x': 0.52, 'hi_o': 0.2, 'hi_slope': 2.5, 'fsti': 0.45,
          'fstf': 0.95, 'kc': 1.0, 'eix': 1.0, 'tr_min_t': 0.0, 'tr_threshold_t': 12.0, 'lat_deg': 40.6875, 'n_simultaneous': True,'n_demand_ref': True, 'n_stress_ag_basis': True, 'n_uptake_rate': 0.03, 'eix_cap': 0.853, 'net_growth_fraction': 0.95, 'ttf50': 0.32,
          'hi_use_thermal_time_fraction': False, 'n_demand_scale': 0.75, 'calibration_factor': 1.0, 'depletion_fraction': 0.55, 'canopy_shape': (5, -14, -15, 16), 'tr_max_mm_day': 8, 'root_max_m': 2.0, 'tt_emergence': 100, 'n_max_conc': 0.07, 'n_dilution_slope': 0.45, 'n_min_conc': 0.002, 'lwp_stress_onset': -1000,
          'lwp_wilting_point': -2100, 'threshold_temp_cold_damage': -10}

CROP_LABELS = {"corn": "Corn (grain)", "silage": "Corn (silage)", "sorghum": "Sorghum", "soybean": "Soybean", "wheat": "Winter wheat", "rotation": "Corn and soybean rotation"}

FERTILIZERS = {k: k.replace("_", " ") for k in E.MINERAL_SOURCES}
FERTILIZERS["uan"] = "UAN (urea ammonium nitrate)"
FERTILIZERS["anhydrous_ammonia"] = "Anhydrous ammonia"
TILLAGE = ["None"] + sorted(E.TILLAGE_IMPLEMENTS)

# ---- what the page may show: everything the page renders comes from here ----
SCHEMA = {
    "api_version": API_VERSION,
    "groups": [
        {"id": "crop", "label": "Crop and years", "fields": [
            {"id": "crop", "label": "Crop", "type": "select", "default": "corn", "options": [[k, v] for k, v in CROP_LABELS.items()]},
            {"id": "start_year", "label": "First year", "type": "number", "default": 1980, "min": 1980, "max": 2016, "step": 1},
            {"id": "end_year", "label": "Last year", "type": "number", "default": 2016, "min": 1980, "max": 2016, "step": 1},
        ]},
        {"id": "planting", "label": "Planting", "applies_to": ["corn", "silage", "sorghum", "soybean", "rotation"], "fields": [
            {"id": "plant_min_doy", "label": "Earliest planting day of year", "type": "number", "default": 110, "min": 60, "max": 200, "step": 1},
            {"id": "plant_max_doy", "label": "Latest planting day of year", "type": "number", "default": 131, "min": 60, "max": 220, "step": 1},
            {"id": "plant_min_soil_t", "label": "Minimum soil temperature (C)", "type": "number", "default": 12.0, "min": 0, "max": 25, "step": 0.5},
        ]},
        {"id": "fertilizer", "label": "Nitrogen fertilizer", "applies_to": ["corn", "silage", "sorghum", "wheat", "rotation"], "fields": [
            {"id": "fert_source", "label": "Source", "type": "select", "default": "uan", "options": [[k, v] for k, v in FERTILIZERS.items()]},
            {"id": "n_rate", "label": "Total N (kg N/ha per year)", "type": "number", "default": 150, "min": 0, "max": 650, "step": 10},
            {"id": "n_timing", "label": "Timing", "type": "select", "default": "planting", "options": [["planting", "All at planting"], ["split", "Two applications (day of year)"]]},
            {"id": "n_doy1", "label": "First application, day of year", "type": "number", "default": 110, "min": 1, "max": 365, "step": 1, "show_if": {"n_timing": "split"}},
            {"id": "n_frac1", "label": "Share applied first (%)", "type": "number", "default": 50, "min": 0, "max": 100, "step": 5, "show_if": {"n_timing": "split"}},
            {"id": "n_doy2", "label": "Second application, day of year", "type": "number", "default": 160, "min": 1, "max": 365, "step": 1, "show_if": {"n_timing": "split"}},
            {"id": "manure_n", "label": "Manure N (kg N/ha per year)", "type": "number", "default": 0, "min": 0, "max": 400, "step": 10, "applies_to": ["corn", "silage", "sorghum", "rotation"]},
            {"id": "manure_source", "label": "Manure type", "type": "select", "default": "dairy", "options": [[k, k.capitalize()] for k in E.MANURE_SOURCES], "show_if": {"manure_n": "!0"}, "applies_to": ["corn", "silage", "sorghum", "rotation"]},
        ]},
        {"id": "tillage", "label": "Tillage", "applies_to": ["corn", "silage", "sorghum", "soybean", "rotation"], "fields": [
            {"id": "tillage_implement", "label": "Implement", "type": "select", "default": "None", "options": [[t, t.replace("_", " ")] for t in TILLAGE]},
            {"id": "tillage_when", "label": "When", "type": "select", "default": "planting", "options": [["planting", "At planting"], ["day", "On a day of year (must fall after planting)"]], "show_if": {"tillage_implement": "!None"}},
            {"id": "tillage_doy", "label": "Day of year", "type": "number", "default": 140, "min": 100, "max": 300, "step": 1, "show_if": {"tillage_when": "day", "tillage_implement": "!None"}},
        ]},
        {"id": "cover", "label": "Cover crop", "applies_to": ["corn", "silage", "sorghum"], "fields": [
            {"id": "cover_crop", "label": "Cover crop after harvest", "type": "select", "default": "none", "options": [["none", "None"], ["rye", "Cereal rye"]]},
            {"id": "cover_plant_doy", "label": "Cover crop planted, day of year", "type": "number", "default": 288, "min": 240, "max": 330, "step": 1, "show_if": {"cover_crop": "!none"}},
            {"id": "cover_kill_doy", "label": "Cover crop killed, day of year (next spring)", "type": "number", "default": 105, "min": 60, "max": 150, "step": 1, "show_if": {"cover_crop": "!none"}},
        ]},
        {"id": "irrigation", "label": "Irrigation", "applies_to": ["corn", "silage", "sorghum", "soybean", "rotation"], "fields": [
            {"id": "irrigation_on", "label": "Irrigate", "type": "select", "default": "no", "options": [["no", "No"], ["auto", "Automatic (refill at a soil water trigger)"]]},
            {"id": "irrigation_trigger", "label": "Trigger (fraction of available water depleted)", "type": "number", "default": 0.5, "min": 0.1, "max": 0.9, "step": 0.05, "show_if": {"irrigation_on": "auto"}},
            {"id": "irrigation_depth_m", "label": "Refill depth (m; each event brings the soil above it to field capacity)", "type": "number", "default": 1.0, "min": 0.3, "max": 2.0, "step": 0.1, "show_if": {"irrigation_on": "auto"}},
            {"id": "irrigation_start", "label": "First day of year events can occur", "type": "number", "default": 150, "min": 1, "max": 365, "step": 1, "show_if": {"irrigation_on": "auto"}},
            {"id": "irrigation_stop", "label": "Last day of year events can occur", "type": "number", "default": 260, "min": 1, "max": 365, "step": 1, "show_if": {"irrigation_on": "auto"}},
        ]},
    ],
    "soil_columns": [["thick", "Thickness (m)"], ["clay", "Clay (%)"], ["sand", "Sand (%)"], ["soc", "Organic C (%)"]],
    "notes": [
        "Weather: gridded daily record 1980 to 2016 at the nearest 0.5 degree cell. Soil: nearest STATSGO2 profile; layers can be edited.",
        "Runs start from the first year with no spin-up, as Cycles does, so early years reflect the starting soil.",
        "A cover crop is planted after the main crop is harvested and killed the next spring, on the same soil water and nitrogen. Cereal rye is simulated as winter cereal with the cereal rye values of the Cycles crop file. Its N losses are counted in the year it is killed.",
        "Soybean fixes its own N, so the fertilizer inputs do not apply to it. In the corn and soybean rotation the first year is corn and the crops then alternate; fertilizer and manure go on the corn years only, and the soybean years draw soil N first and fix the rest. Table means and the chart mix the two crops, so read the years of each crop separately. Winter wheat is planted in the fall (day 289) with its own fixed planting and tillage.",
    ],
}

ANNUAL_COLUMNS = [
    ["year", "Year", ""], ["plant_doy", "Planted (day)", "doy"], ["harvest_doy", "Harvest (day)", "doy"],
    ["grain", "Grain (or forage) yield", "Mg/ha"], ["total", "Total biomass", "Mg/ha"], ["ag", "Aboveground biomass", "Mg/ha"],
    ["n_uptake", "Crop N uptake", "kg N/ha"], ["n_leached", "Nitrate leaching", "kg N/ha"], ["n_denitrified", "Denitrification", "kg N/ha"],
    ["n_volatilized", "Ammonia volatilization", "kg N/ha"], ["n2o", "N2O emission", "kg N/ha"], ["runoff", "Runoff", "mm"],
    ["n_mineral_end", "Mineral N at season end", "kg N/ha"], ["winter_killed", "Winter killed", ""],
]
ROTATION_COLUMNS = [["crop", "Crop", ""], ["n_fixed", "N fixed by soybean", "kg N/ha"]]
COVER_COLUMNS = [["cover_ag", "Cover crop biomass at kill", "Mg/ha"], ["cover_n_uptake", "Cover crop N uptake", "kg N/ha"]]
DAILY_COLUMNS = [
    ["doy", "Day of year", ""], ["ttf", "Thermal time fraction", "-"], ["canopy", "Light interception", "-"], ["water_stress", "Water stress factor", "-"],
    ["n_stress", "N stress factor", "-"], ["ag_mg_ha", "Aboveground biomass", "Mg/ha"], ["n_plant", "Crop N", "kg N/ha"], ["n_no3", "Soil nitrate", "kg N/ha"],
    ["n_nh4", "Soil ammonium", "kg N/ha"], ["theta1", "Water content layer 1", "m3/m3"], ["theta2", "Water content layer 2", "m3/m3"],
    ["theta3", "Water content layer 3", "m3/m3"], ["theta4", "Water content layer 4", "m3/m3"],
]

_STATE = {"wx": None, "soil": None, "lat": None}


# Soybean with the legume N path (2026-10-23, rotation support): soil N is drawn first, fixation fills the unmet new-growth demand (Kemanian 2024 Sec 2.5), N stress off. Used by the rotation option;
# n_demand_scale 0.74 is measured on Cycles' soybean plant N (203 kg N/ha, 24 sites), class D in the ledger.
_SOYBEAN_N = dict(_SOYBEAN, legume_n=True, n_demand_ref=True, n_uptake_rate=0.03, n_stress_ag_basis=True, n_demand_scale=0.74)

# ---- what the page shows scientists about the model (single source: the page reads info(), it never hard-codes these) ----
ENGINE_INFO = {
    "name": "Rhizo",
    "version": "2026-10-24",
    "summary": "Rhizo is a daily-step crop, soil water, carbon and nitrogen model written from scratch in Python and run in your browser. Its equations come from the published Cycles paper and its supplement (Kemanian et al. 2024) and from the literature cited below; where the sources give no equation the model uses a measured relationship and says so. It is tested against the Cycles model and against observations.",
    "validation_note": "Agreement with Cycles v1.5.20 on identical weather and soil, held-out sites, 1980 to 2016 (94 sites for spring crops, 60 for winter wheat). r is the correlation across all site-years pooled; bias and error are the model minus Cycles in grain yield. Cycles itself disagrees with its own variants by about 0.17 to 1.4 Mg/ha depending on what changes.",
    "validation_columns": ["Crop", "N rate (kg N/ha)", "r", "Bias (%)", "Mean abs error (Mg/ha)"],
    "validation": [
        ["Corn", "0 / 150 / 400", "0.96 / 0.92 / 0.96", "-10 / -1 / -6", "0.48 / 0.97 / 0.86"],
        ["Silage corn", "0 / 150 / 400", "0.94 / 0.92 / 0.95", "-9 / -5 / -7", "0.88 / 1.70 / 1.61"],
        ["Sorghum", "0 / 150 / 400", "0.94 / 0.88 / 0.92", "-15 / -6 / -11", "0.52 / 1.11 / 1.18"],
        ["Soybean", "none", "0.96", "-2", "0.33"],
        ["Winter wheat", "0 / 90 / 150", "0.93 / 0.87 / 0.87", "0 / +3 / -1", "0.36 / 0.65 / 0.74"],
    ],
    "observations": [
        "County yields (USDA NASS, 94 counties, 1982 to 2016): year-to-year agreement within a county, median r 0.43 for corn (Cycles 0.38), 0.34 soybean, 0.31 silage, 0.15 wheat; mean level 0.93 of the county corn mean.",
        "Mead, Nebraska flux towers and measured yields: corn and soybean yields as close to the measurements as Cycles' (for example irrigated corn 12.4 modelled, 11.7 measured Mg/ha).",
        "Corn after soybean in a rotation: 0.96 to 0.99 of Cycles' yield with no nitrogen, 0.93 to 0.95 at 150 kg N/ha.",
    ],
    "sources": [
        "Kemanian, A.R., Shi, Y., White, C.M., Montes, F., Stockle, C.O., Huggins, D.R., et al., 2024. The Cycles agroecosystem model: fundamentals, testing, and applications. Computers and Electronics in Agriculture 227, 109510, and its supplement (growth, partition, canopy, water, carbon and nitrogen equations).",
        "Pravia, M.V., Kemanian, A.R., et al., 2019. Soil carbon saturation, productivity, and carbon and nitrogen cycling in crop-pasture rotations. Agricultural Systems 171, 13-22 (decomposition constants).",
        "Kemanian, A.R. and Williams, J.R., 2011. APEX model upgrades, CEAP (denitrification and nitrous oxide); Stockle, C.O. and Campbell, G.S., 1989 (nitrification temperature, plant water uptake); Saxton, K.E. and Rawls, W.J., 2006 (soil hydraulic properties); Allen et al., FAO-56 (reference evapotranspiration).",
    ],
}


def info():
    return json.dumps(ENGINE_INFO)


def schema():
    return json.dumps(SCHEMA)


def load_site(site_json):
    """site_json: {lat, weather: {fields: [...], years: {year: {doy: [values]}}}, soil: [{thick, clay, sand, soc}]}. Stored for run()."""
    s = json.loads(site_json)
    fields = s["weather"]["fields"]
    wx = {}
    for y, days in s["weather"]["years"].items():
        wx[int(y)] = {int(d): dict(zip(fields, v), doy=int(d)) for d, v in days.items()}
    _STATE.update(wx=wx, soil=s["soil"], lat=float(s["lat"]))
    return json.dumps({"years": [min(wx), max(wx)], "layers": len(s["soil"])})


def _make_layers(soil):
    def ml():
        L = []
        for l in soil:
            h = E.saxton_rawls(l["sand"], l["clay"], l["soc"] * E.OM_FROM_SOC, l.get("fc"), l.get("pwp"), l.get("bd"))
            L.append(dict(thick=l["thick"], fc=h["fc"], pwp=h["pwp"], sat=h["sat"], theta=h["pwp"] + E.INITIAL_MOISTURE_FRACTION * (h["fc"] - h["pwp"]),
                          ksat_mm_day=h["ksat_mm_day"], psi_e_kpa=h["psi_e_kpa"], B=h["B"]))
        return L
    return ml


def _applications(cfg, crop_key):
    """(kwargs fragment) for the fertilizer schedule: one lump at planting through n_rate_kg_ha, or dated applications."""
    n = float(cfg.get("n_rate", 0) or 0)
    if cfg.get("n_timing") == "split" and n > 0:
        f = max(0.0, min(100.0, float(cfg.get("n_frac1", 50)))) / 100.0
        return dict(n_rate_kg_ha=None, n_applications=[(int(cfg.get("n_doy1", 110)), n * f), (int(cfg.get("n_doy2", 160)), n * (1.0 - f))])
    return dict(n_rate_kg_ha=n)


def _row_out(y, r, carry):
    leach = r.get("n_leached_kg_ha", 0.0); den = r.get("n_denitrified_kg_ha", 0.0); vol = r.get("n_volatilized_pool_kg_ha", 0.0); n2o = r.get("n2o_emitted_kg_ha", 0.0)
    if carry and "fallow_n_leached" in r:   # add the off-season windows so totals are calendar-year, like Cycles' annual N file
        leach += r["fallow_n_leached"]; den += r["fallow_n_denitrified"]; vol += r["fallow_n_volatilized"]; n2o += r.get("fallow_n2o", 0.0)
    return dict(year=y, plant_doy=r.get("plant_doy"), harvest_doy=r.get("last_doy"), grain=r.get("forage") if r.get("_forage") else r.get("grain"), total=r.get("total"), ag=r.get("ag"),
                n_uptake=r.get("n_uptake_kg_ha"), n_leached=leach, n_denitrified=den, n_volatilized=vol, n2o=n2o, runoff=r.get("runoff_mm"),
                n_mineral_end=r.get("n_remaining_kg_ha"), winter_killed=bool(r.get("winter_killed")),
                cover_ag=(r.get("cover") or {}).get("ag"), cover_n_uptake=(r.get("cover") or {}).get("n_uptake"),
                crop=r.get("_crop_label"), n_fixed=r.get("n_fixed_kg_ha"))


def _daily_out(r):
    h = r.get("history") or []
    out = []
    for d in h:
        th = d.get("theta") or []
        out.append([d.get("doy"), d.get("ttf"), d.get("canopy"), d.get("water_stress"), d.get("n_stress"), d.get("ag_mg_ha"), d.get("n_plant"), d.get("n_no3"), d.get("n_nh4")]
                   + [th[i] if i < len(th) else None for i in range(4)])
    return out


def _rye_crop(lat, soil):
    """Cereal rye cover crop: the winter-wheat configuration with the two WinterRye crop-file values that differ (flowering at Pmax 290, transpiration threshold 8 C); nothing is harvested and its plant N returns with its residue."""
    c = dict(_WHEAT); c["lat_deg"] = lat
    c.pop("rhizo_rr", None); c.pop("rhizo_root_n_share", None)   # rye was validated without the lost-root N sink; untested for rye, so unchanged
    c["vern"] = dict(E.WINTER_PHENOLOGY); c["vern"]["tt_flower_pmax"] = 290.0; c["base_t"] = E.WINTER_PHENOLOGY["base_t"]
    c.update(hi_x=0.0, hi_o=0.0, calibration_factor=1.0, tr_threshold_t=8.0, residue_n_from_plant=True)
    c["make_layers"] = _make_layers(soil)
    return c


def _spring_chain(cfg, crop_key, wx, soil, lat):
    rotation = crop_key == "rotation"
    crop = dict(_SILAGE if crop_key == "silage" else _SOYBEAN_N if crop_key == "soybean" else _CORN)
    if crop_key == "sorghum":
        crop.update(_SORGHUM_OVER)
    crop["lat_deg"] = lat
    crop["make_layers"] = _make_layers(soil)
    soy = crop_key == "soybean"
    kw = E.standard_kwargs(soil, 0.0 if soy else float(cfg.get("n_rate", 0) or 0))   # soybean runs the legume N path (2026-10-23): soil N first, fixation fills the rest, no fertilizer
    if soy:
        kw["n_rate_kg_ha"] = 0
    if not soy:
        kw.update(_applications(cfg, crop_key))
        src = cfg.get("fert_source", "uan")
        if float(cfg.get("n_rate", 0) or 0) > 0:
            kw["fertilizer_source"] = src
        if float(cfg.get("manure_n", 0) or 0) > 0:
            kw["manure_n_kg_ha"] = float(cfg["manure_n"]); kw["manure_source"] = cfg.get("manure_source", "dairy")
    if crop_key == "silage":
        kw["harvest_ttf"] = 0.85   # Cycles harvests silage at 85 percent of maturity
    ti = cfg.get("tillage_implement", "None")
    if ti and ti != "None":
        kw["tillage_clay_frac"] = float(soil[0]["clay"]) / 100.0   # the tillage decomposition speed-up depends on the site's topsoil clay (default 0.21 is not the site)
        kw["tillage_implement"] = ti; kw["tillage_doy"] = "planting" if cfg.get("tillage_when", "planting") == "planting" else int(cfg.get("tillage_doy", 140))
    if cfg.get("irrigation_on") == "auto":
        # Cycles' AUTO_IRRIGATION: the trigger is the fraction of plant available water DEPLETED; an event refills the layers down to the depth to field capacity
        kw["irrigation_trigger_frac"] = 1.0 - float(cfg.get("irrigation_trigger", 0.5))
        _z, _n = 0.0, 0
        for _l in soil:
            _n += 1; _z += _l["thick"]
            if _z >= float(cfg.get("irrigation_depth_m", 1.0)): break
        kw["irrigation_refill_layers"] = _n
        kw["irrigation_window"] = (int(cfg.get("irrigation_start", 150)), int(cfg.get("irrigation_stop", 260)))
    kw["record_history"] = True
    first = int(cfg["start_year"]); last = int(cfg["end_year"])
    yrs = [y for y in sorted(wx) if first <= y <= last]
    pw = (int(cfg.get("plant_min_doy", 110)), int(cfg.get("plant_max_doy", 131)))
    cover = None
    if cfg.get("cover_crop", "none") not in ("none", "", None):
        if soy or rotation:
            raise ValueError("Cover crops are available for corn, silage corn and sorghum (not for the rotation).")
        cp, ck = int(cfg.get("cover_plant_doy", 288)), int(cfg.get("cover_kill_doy", 105))
        if ck >= pw[0]:
            raise ValueError("The cover crop must be killed before the earliest planting day.")
        cover = dict(crop=_rye_crop(lat, soil), plant_doy=cp, kill_doy=ck)
    year_plan = None
    if rotation:
        # corn in the first year and every second year after, soybean (legume N path: soil N first, fixation fills the rest) in between; the same planting window for both
        soy_crop = dict(_SOYBEAN_N); soy_crop["lat_deg"] = lat; soy_crop["make_layers"] = crop["make_layers"]
        kw_soy = {k: v for k, v in kw.items() if k not in ("n_applications", "fertilizer_source", "manure_n_kg_ha", "manure_source")}
        kw_soy["n_rate_kg_ha"] = 0
        year_plan = {y: (dict(crop=crop) if (y - yrs[0]) % 2 == 0 else dict(crop=soy_crop, kw_replace=kw_soy)) for y in yrs}
    res = E.simulate_continuous(wx, crop, years=yrs, plant_window=pw, plant_min_soil_t=float(cfg.get("plant_min_soil_t", 12.0)), carry_n=True, cover=cover, year_plan=year_plan, **kw)
    if rotation:
        for y, r in res.items():
            r["_crop_label"] = "Corn" if (y - yrs[0]) % 2 == 0 else "Soybean"
    if crop_key == "silage":
        for r in res.values():
            r["_forage"] = True
    return res, True


def _wheat_chain(cfg, wx, soil, lat):
    """Fall-to-fall winter wheat chain (the validated runner): planted at day 289, harvest the next summer, N applications as given."""
    crop = dict(_WHEAT); crop["lat_deg"] = lat
    crop["vern"] = dict(E.WINTER_PHENOLOGY); crop["base_t"] = E.WINTER_PHENOLOGY["base_t"]
    ml = _make_layers(soil); crop["make_layers"] = ml
    N = float(cfg.get("n_rate", 0) or 0)
    wf = [(y, d, wx[y][d]) for y in sorted(wx) for d in sorted(wx[y])]
    fi = {(y, d): i for i, (y, d, _) in enumerate(wf)}
    rows = lambda a, b: [x for (_, _, x) in wf[a:b]]
    layers = ml(); nstate = None; sp = None; prev_end = None; out = {}
    base = E.standard_kwargs(soil, 0); base.pop("fertilizer_source", None); base["n_rate_kg_ha"] = None
    first = int(cfg["start_year"]); last = int(cfg["end_year"])
    for y in sorted(wx)[:-1]:
        if (y, 288) not in fi:
            continue
        start = fi[(y, 288)]
        fallow = rows(fi[(y, 1)], start) if prev_end is None else rows(prev_end, start)
        if nstate is None:
            nstate = dict(n_nh4=0.0, n_no3=0.0, tsoil_lag=(wf[start][2]["tx"] + wf[start][2]["tn"]) / 2.0, no3_layers=[0.0] * len(layers), rel_hist=[])
        de = dict(de=0.0, tew=E.compute_tew(layers[0]["fc"], layers[0]["pwp"]), rew=E.REW_DEFAULT_MM)
        E._DIAG_YEAR = y; E._FORCE_CUR = None
        E.run_fallow_n_window(layers, fallow, nstate, sp, lat_deg=lat, de_state=de, model_denitrification=True, model_volatilization=True)
        nstate.pop("n2o", None)
        kw = dict(base); kw.update(initial_n_state=dict(nstate), initial_layers=layers, spinup_rows=None, wue_co2_scale=E.CO2_PPM_BY_YEAR.get(y, E.CO2_REF_PPM) / E.CO2_REF_PPM, record_history=True)
        fall_n = min(60.0, N)
        if N > 0:
            kw["n_applications"] = [(289, fall_n), (75, N - fall_n)] if N > fall_n else [(75, N)]
            if cfg.get("n_timing") == "split":
                f = max(0.0, min(100.0, float(cfg.get("n_frac1", 50)))) / 100.0
                kw["n_applications"] = [(int(cfg.get("n_doy1", 289)), N * f), (int(cfg.get("n_doy2", 75)), N * (1.0 - f))]
            kw["fertilizer_source"] = cfg.get("fert_source", "uan")
        else:
            kw["n_rate_kg_ha"] = 0
        if sp is not None:
            kw["sixpool_initial_state"] = sp
        # pre-pass for the season's own maturity thermal time (TTf = plant age over thermal time at maturity, paper Sec 2.3; 2026-10-23)
        _k = dict(kw); _k["initial_n_state"] = dict(nstate); _k["initial_layers"] = copy.deepcopy(layers); _k["record_history"] = False
        if sp is not None:
            _k["sixpool_initial_state"] = copy.deepcopy(sp)
        _c = dict(crop); _c["season_tt_end"] = E.simulate_season(rows(start, start + 400), crop, **_k)["tt_cum_end"]
        res = E.simulate_season(rows(start, start + 400), _c, **kw)
        layers = res["final_layers"]; nstate = dict(res["final_n_state"]); sp = copy.deepcopy(res.get("sixpool_final_state"))
        prev_end = start + len(res["history"])
        if first <= y + 1 <= last:
            out[y + 1] = res
    return out, False


def run(config_json):
    cfg = json.loads(config_json)
    wx, soil, lat = _STATE["wx"], _STATE["soil"], _STATE["lat"]
    if wx is None:
        raise ValueError("No site loaded.")
    if "soil" in cfg and cfg["soil"]:
        soil = cfg["soil"]
    crop_key = cfg.get("crop", "corn")
    if crop_key not in CROP_LABELS:
        raise ValueError("Unknown crop %r" % crop_key)
    if int(cfg["end_year"]) < int(cfg["start_year"]):
        raise ValueError("Last year is before first year.")
    res, carry = _wheat_chain(cfg, wx, soil, lat) if crop_key == "wheat" else _spring_chain(cfg, crop_key, wx, soil, lat)
    annual = []; daily = {}
    for y in sorted(res):
        annual.append(_row_out(y, res[y], carry)); daily[str(y)] = _daily_out(res[y])
    notes = []
    if crop_key == "wheat":
        notes.append("Wheat N losses cover the growing season only (fall planting to harvest).")
    covered = any(r.get("cover_ag") is not None for r in annual)
    return json.dumps(dict(annual=annual, annual_columns=ANNUAL_COLUMNS + (ROTATION_COLUMNS if crop_key == "rotation" else []) + (COVER_COLUMNS if covered else []), daily=daily, daily_columns=DAILY_COLUMNS, notes=notes, api_version=API_VERSION))
