"""Extract management, soil and crop observations from an AmeriFlux BIF xlsx into a small JSON the scorer reads.
    python3 bif_extract.py "AMF_US-Ne3_BIF_*.xlsx"   (needs openpyxl; writes <SITE>_bif.json next to the file)"""
import sys, json, os, collections, openpyxl
def run(path):
    rows = [r for r in openpyxl.load_workbook(path, read_only=True, data_only=True)["AMF-BIF"].iter_rows(values_only=True)][1:]
    site = rows[0][0]
    by = collections.defaultdict(list); tmp = collections.defaultdict(lambda: collections.defaultdict(dict))
    for s, g, grp, v, d in rows: tmp[grp][g][v] = d
    for grp, recs in tmp.items(): by[grp] = list(recs.values())
    one = lambda grp: (by.get(grp) or [{}])[0]
    out = dict(site=site, location=one("GRP_LOCATION"), soil_texture_pct=one("GRP_SOIL_TEX"), soil_depth_cm=one("GRP_SOIL_DEPTH"), climate=one("GRP_CLIM_AVG"),
               soil_classification=one("GRP_SOIL_CLASSIFICATION").get("SOIL_CLASSIFICATION"),
               planting=sorted(by.get("GRP_DM_PLANTING", []), key=lambda r: r.get("DM_DATE_START") or ""),
               fertilizer=sorted(by.get("GRP_DM_FERT_M", []), key=lambda r: r.get("DM_DATE_START") or ""),
               irrigation=by.get("GRP_DM_IRRIG", []), tillage=sorted(by.get("GRP_DM_TILL", []), key=lambda r: r.get("DM_DATE") or ""),
               production=sorted(by.get("GRP_AG_PROD_CROP", []), key=lambda r: r.get("AG_PROD_DATE_START") or ""),
               biomass=sorted(by.get("GRP_AG_BIOMASS_CROP", []), key=lambda r: r.get("AG_BIOMASS_DATE") or ""),
               lai=sorted(by.get("GRP_LAI", []), key=lambda r: r.get("LAI_DATE") or ""), groups_present=sorted(by))
    dst = os.path.join(os.path.dirname(os.path.abspath(path)), f"{site}_bif.json"); json.dump(out, open(dst, "w"), indent=1)
    print(site, {k: len(v) for k, v in out.items() if isinstance(v, list)}, "->", dst)
if __name__ == "__main__":
    for p in sys.argv[1:]: run(p)
