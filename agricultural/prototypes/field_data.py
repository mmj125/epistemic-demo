"""
Real, committed-data field resolver -- a Python port of field_selector.js's
own decode logic (tileForPoint / decodeCellWeather / nearestSoilCell /
soilLayersForCell), checked line-by-line against that file rather than
re-derived from memory or guessed at, since a silently wrong byte-layout
assumption here would produce plausible-looking garbage, not an obvious
crash.

Exists specifically so pattern_assertions.py (and any other script that
needs real multi-site weather/soil) can run WITHOUT /tmp/cycles-run, which
this container has repeatedly lost to mid-session reprovisioning (see
CLAUDE.md's "Operational note for a fresh conversation" and "Caught
directly for the first time" entries) -- everything this module reads is
committed to the repo:
  - agricultural/prototypes/weather-tiles/ -- real NLDAS-2-derived weather,
    50 tiles covering the CONUS, 1980-2016, 0.5-degree resolution.
  - agricultural/prototypes/statsgo2_soil_grid.json.gz -- real STATSGO2 soil
    profiles, ~3044 cells nationally.

Not a wholesale copy of field_selector.js -- only the read path (no KML
parsing, no upload UI) -- but the actual tile-key math, byte layout, and
soil-cell nearest-neighbor logic are the same, verified against a live
resolve (Rock Springs' own coordinates correctly resolve to the Hazleton
soil series, matching field_selector.js's own already-documented result)
before this was trusted for anything.
"""
import gzip
import json
import math
import os
import struct

PROTO_DIR = os.path.dirname(__file__)
WEATHER_TILES_DIR = os.path.join(PROTO_DIR, "weather-tiles")
SOIL_GRID_PATH = os.path.join(PROTO_DIR, "statsgo2_soil_grid.json.gz")
TILE_DEG = 5
DEFAULT_SUBSOIL_SOC_PCT = 0.2  # matches field_selector.js's own disclosed default


def is_leap_year(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def all_year_doys(y0, y1):
    out = []
    for y in range(y0, y1 + 1):
        n = 366 if is_leap_year(y) else 365
        for d in range(1, n + 1):
            out.append((y, d))
    return out


def tile_for_point(lat, lon, tile_deg=TILE_DEG):
    lat0 = math.floor(lat / tile_deg) * tile_deg
    lon0 = math.floor(lon / tile_deg) * tile_deg
    return lat0, lon0, f"{lat0}_{lon0}"


_MANIFEST_CACHE = None


def load_manifest():
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        with open(os.path.join(WEATHER_TILES_DIR, "manifest.json")) as f:
            _MANIFEST_CACHE = json.load(f)
    return _MANIFEST_CACHE


_TILE_BYTES_CACHE = {}


def load_tile_bytes(manifest, key):
    if key not in _TILE_BYTES_CACHE:
        entry = manifest["tiles"].get(key)
        if entry is None:
            _TILE_BYTES_CACHE[key] = (None, None)
        else:
            path = os.path.join(WEATHER_TILES_DIR, entry["file"])
            with gzip.open(path, "rb") as f:
                _TILE_BYTES_CACHE[key] = (f.read(), entry)
    return _TILE_BYTES_CACHE[key]


def decode_cell_weather(data_bytes, cell_index, manifest, tile_entry):
    """Returns {year: {doy: row_dict}}, row_dict carrying its own "doy" plus
    every field in manifest["fields"] -- the exact shape simulate_season()
    expects for one weather row. Byte layout matches
    field_selector.js's decodeCellWeather() exactly: cell-major blocks, each
    block a flat day-major/field-minor little-endian int16 array, scaled per
    manifest["scale"]."""
    days = all_year_doys(manifest["years"][0], manifest["years"][1])
    if tile_entry.get("n_days") is not None and tile_entry["n_days"] != len(days):
        raise ValueError(
            "Tile n_days doesn't match the manifest's declared year range -- "
            "decoder is out of sync with the real packer, do not trust this data."
        )
    fields = manifest["fields"]
    n_fields = len(fields)
    records_per_cell = len(days) * n_fields
    offset_values = cell_index * records_per_cell
    values = struct.unpack_from(f"<{records_per_cell}h", data_bytes, offset_values * 2)
    scale = manifest["scale"]
    out = {}
    for i, (year, doy) in enumerate(days):
        row = {"doy": doy}
        base = i * n_fields
        for f_idx, field in enumerate(fields):
            row[field] = values[base + f_idx] * scale[field]
        out.setdefault(year, {})[doy] = row
    return out


def resolve_field_weather(lat, lon):
    """Returns (weather_by_year, distance_deg) for the nearest real committed
    weather cell to (lat, lon). weather_by_year is None if the point falls
    outside real tile coverage (open ocean, Great Lakes, outside CONUS)."""
    manifest = load_manifest()
    _, _, key = tile_for_point(lat, lon, manifest.get("tile_deg", TILE_DEG))
    data, entry = load_tile_bytes(manifest, key)
    if data is None:
        return None, math.inf
    best_idx, best_dist = 0, math.inf
    for idx, (clat, clon) in enumerate(entry["cells"]):
        d = math.hypot(clat - lat, clon - lon)
        if d < best_dist:
            best_dist, best_idx = d, idx
    return decode_cell_weather(data, best_idx, manifest, entry), best_dist


_SOIL_GRID_CACHE = None


def load_soil_grid():
    global _SOIL_GRID_CACHE
    if _SOIL_GRID_CACHE is None:
        with gzip.open(SOIL_GRID_PATH, "rt") as f:
            _SOIL_GRID_CACHE = json.load(f)
    return _SOIL_GRID_CACHE


def nearest_soil_cell(lat, lon):
    grid = load_soil_grid()
    best, best_dist = None, math.inf
    for cell in grid:
        d = math.hypot(cell["lat"] - lat, cell["lon"] - lon)
        if d < best_dist:
            best_dist, best = d, cell
    return best, best_dist


def soil_layers_raw_for_cell(cell):
    """SOIL_LAYERS_RAW shape (thick/clay/sand/soc), the same shape
    run_validation.py hand-curates for Rock Springs -- a resolved real cell
    can be handed straight to the same make_layers()-style builder."""
    return [
        dict(thick=l["thick"], clay=l["clay"], sand=l["sand"],
             soc=(DEFAULT_SUBSOIL_SOC_PCT if l["soc"] is None else l["soc"]))
        for l in cell["layers"]
    ]


def resolve_field_soil(lat, lon):
    """Returns (soil_layers_raw, distance_deg, real_series_name)."""
    cell, dist = nearest_soil_cell(lat, lon)
    return soil_layers_raw_for_cell(cell), dist, cell.get("compname")


# Real preset sites this project already validated and documented in
# CLAUDE.md ("Four preset sites added...", 2026-09-17) -- reused here rather
# than picking new coordinates, so every pattern check below is checkable
# against this project's own prior findings, not a fresh unverified location.
PRESET_SITES = {
    "rock_springs": (40.7093, -77.9478),   # Hazleton series, PA Ridge-and-Valley
    "iowa": (42.0, -93.6),                  # Canisteo series, deep clayey prairie
    "kansas": (37.97, -100.87),             # Manter series, sandy semi-arid High Plains
    "maryland": (38.5, -75.8),              # Othello series, silty Chesapeake coastal plain
    "north_dakota": (48.23, -101.30),       # Barnes series, glacial-till prairie
}
