#!/bin/bash
# usage: crops_driver.sh  ; runs old (worktree) and new (repo) for soy silage sorghum, then wheat
OLD=/tmp/w/oldwt/agricultural/prototypes; NEW=/home/user/epistemic-demo/agricultural/prototypes
runmulti(){ # dir tag crop nlevels
  cd $1; for i in 0 1 2 3; do ( CROPSEL=$3 REGIONAL=0 YEAR_STEP=2 N_LEVELS=$4 LEAD_YEARS=continuous BIGSET=/tmp/w/fr_$i.json OUT_JSON=/tmp/w/$2_$i.json python3 run_validation_multisite.py > /tmp/w/$2_$i.log 2>&1 ) & done; wait; echo done $2 >> /tmp/w/crops_progress.txt; }
runwheat(){ cd $1; for off in 0 1; do FALLN=60 SITEOFF=$off NSITES=30 OUT_JSON=/tmp/w/$2_$off.json python3 run_validation_multisite_wheat.py > /tmp/w/$2_$off.log 2>&1; done; echo done $2 >> /tmp/w/crops_progress.txt; }
: > /tmp/w/crops_progress.txt
runmulti $OLD soyold soy 0; runmulti $NEW soynew soy 0
runmulti $OLD silold silage 0,150,400; runmulti $NEW silnew silage 0,150,400
runmulti $OLD sorold sorghum 0,150,400; runmulti $NEW sornew sorghum 0,150,400
runwheat $OLD wheatold; runwheat $NEW wheatnew
echo ALLDONE >> /tmp/w/crops_progress.txt
