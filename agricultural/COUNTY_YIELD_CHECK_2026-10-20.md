# Engine and Cycles against USDA county yields, 2026-10-20

Data: NASS Quick Stats county survey yields (bulk file `qs.crops_20261020`), 1982 to 2016, for the county containing each of the 94 fresh sites (`prototypes/sitesets/fresh94_county.json`, Census geocoder; subset in `prototypes/data/nass_county_yield_fresh94.csv`). Observed: corn grain, soybean, winter wheat (all production practices, bu/acre) and corn silage (tons/acre, 35% dry matter assumed). Engine: `engine_api`, N=150 (corn, silage, wheat with 60 kg in the fall), soybean without N. Cycles: the reference cache, same weather, soil and N. Scripts: `prototypes/county_runs_2026_10_20.py`, `prototypes/county_compare_2026_10_20.py`. Each series is detrended linearly per site (county yields carry a hybrid and management trend the models do not). Sites need 15 or more years of county data.

## Year-to-year agreement within a site (median detrended correlation)

| Crop | Sites | Engine | Cycles | Engine minus Cycles, paired |
|---|---|---|---|---|
| Corn grain | 69 | 0.45 | 0.38 | +0.033 [+0.002, +0.066] |
| Corn silage | 34 | 0.37 | 0.34 | +0.060 [+0.017, +0.109] |
| Soybean | 56 | 0.34 | 0.33 | +0.004 [-0.023, +0.028] |
| Winter wheat | 51 | 0.18 | 0.22 | -0.016 [-0.062, +0.031] |

The engine tracks county year-to-year variation about as well as Cycles, and slightly better for corn. Both are modest: a median r of 0.4 explains about 16 to 20% of the county variance.

## Level (mean 2007 to 2016, model over county)

Corn x0.95 engine, x0.89 Cycles (east of 97.5 W: 1.03 and 0.95; west 0.64 and 0.65, irrigation in the county data). Soybean x1.22 and x1.31. Silage x1.09 and x1.10. Winter wheat x1.59 and x1.43: both models over-predict wheat by about half.

## Extreme years, eastern corn sites (deviation from each series' own trend)

| Year | Observed | Engine | Cycles |
|---|---|---|---|
| 1983 | -10% | -9% | -5% |
| 1988 | -23% | -26% | -43% |
| 1993 | -17% | +3% | +7% |
| 2012 | -12% | -36% | -41% |

Drought years are exaggerated (2012 about three times the observed loss, by both models) and the 1993 cold, wet year is missed entirely by both.

## Caveats

County mean yield against one point simulation: irrigation (west), hybrid and management mix, soil variation inside the county and county-level noise all lower the ceiling. The 0.5 degree weather cell is not the county. Wheat county yields mix classes and regions. Sorghum was not pulled. N rate is a single assumed value.
