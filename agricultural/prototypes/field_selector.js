/*
 * Client-side plumbing for "pick any field in the CONUS" (Option 2 from
 * CLAUDE.md's Agricultural unit section): parse a student-uploaded KML
 * boundary into a real polygon centroid, work out which pre-tiled weather
 * cell that centroid falls in, and fetch/decompress that tile the same way
 * meteorology/energy-balance-sandbox.html already fetches its CERES/ERA5
 * fine tiles (DecompressionStream("gzip"), no external library).
 *
 * This file has no dependency on the actual CONUS tile data, which doesn't
 * exist yet -- it's written and tested against synthetic KML/tiles so the
 * plumbing is proven before Matt's Colab export lands. Once that export
 * exists (see the manifest shape TILE_MANIFEST_SHAPE below), only
 * TILE_BASE_URL needs to point at the real GitHub Release and this is
 * ready to wire into engine-demo.html.
 */

const TILE_DEG = 5; // each tile covers a 5x5 degree box
// Fine-tile scale (weather resolution inside each tile) is a manifest
// property (see decodeTile), not hardcoded here -- this file only needs to
// know which 5x5 box a point falls in, not the tile's internal grid.

// Example of what the real manifest.json (hosted alongside the tiles on the
// GitHub Release) needs to declare -- not used at runtime, just documents
// the contract loadManifest()/decodeTile() expect.
const TILE_MANIFEST_SHAPE = {
  tile_deg: TILE_DEG,
  resolution_deg: 0.5,       // native weather grid resolution inside each tile
  years: [1980, 2016],
  fields: ["pp", "tx", "tn", "solar", "rhx", "rhn", "wind"], // same order/units as RockSprings.weather
  scale: { pp: 0.1, tx: 0.1, tn: 0.1, solar: 0.01, rhx: 0.1, rhn: 0.1, wind: 0.01 }, // int16 quantization, per field
  tiles: {
    // "35_-80": {lat0: 35, lon0: -80, file: "tile_35_-80.bin.gz"}, ...
  },
};

function parseKML(kmlText) {
  const doc = new DOMParser().parseFromString(kmlText, "text/xml");
  if (doc.querySelector("parsererror")) {
    throw new Error("That file isn't valid KML/XML.");
  }
  const placemarks = Array.from(doc.getElementsByTagName("Placemark"));
  if (placemarks.length === 0) throw new Error("No Placemark found in this KML file.");
  if (placemarks.length > 1) {
    console.warn(`KML has ${placemarks.length} placemarks; using the first one (a field is one boundary).`);
  }
  const pm = placemarks[0];

  const point = pm.getElementsByTagName("Point")[0];
  if (point) {
    const coordText = point.getElementsByTagName("coordinates")[0]?.textContent?.trim();
    if (!coordText) throw new Error("Point placemark has no coordinates.");
    const [lng, lat] = coordText.split(",").map(Number);
    return { kind: "point", lat, lng };
  }

  const ring = pm.getElementsByTagName("LinearRing")[0] || pm.getElementsByTagName("coordinates")[0];
  const coordEl = ring?.tagName === "LinearRing" ? ring.getElementsByTagName("coordinates")[0] : ring;
  if (!coordEl) throw new Error("No Point or Polygon coordinates found in this KML file.");

  const raw = coordEl.textContent.trim().split(/\s+/);
  const vertices = raw.map((triplet) => {
    const [lng, lat] = triplet.split(",").map(Number);
    return { lat, lng };
  }).filter((v) => Number.isFinite(v.lat) && Number.isFinite(v.lng));

  if (vertices.length < 3) throw new Error("Polygon needs at least 3 valid vertices.");
  return { kind: "polygon", vertices };
}

// Real area-weighted polygon centroid (the shoelace-formula centroid, not a
// naive average of vertices, which is visibly wrong for irregular field
// shapes -- e.g. an L-shaped parcel's vertex-average sits outside the field
// entirely, while the area-weighted centroid stays inside it).
function polygonCentroid(vertices) {
  let signedArea = 0, cx = 0, cy = 0;
  const n = vertices.length;
  for (let i = 0; i < n; i++) {
    const p0 = vertices[i], p1 = vertices[(i + 1) % n];
    const cross = p0.lng * p1.lat - p1.lng * p0.lat;
    signedArea += cross;
    cx += (p0.lng + p1.lng) * cross;
    cy += (p0.lat + p1.lat) * cross;
  }
  signedArea *= 0.5;
  if (Math.abs(signedArea) < 1e-12) {
    // Degenerate (near-zero-area) polygon, e.g. all vertices nearly collinear
    // or duplicated -- fall back to a plain vertex average rather than
    // dividing by ~zero.
    const lat = vertices.reduce((s, v) => s + v.lat, 0) / n;
    const lng = vertices.reduce((s, v) => s + v.lng, 0) / n;
    return { lat, lng, degenerate: true };
  }
  cx /= (6 * signedArea);
  cy /= (6 * signedArea);
  return { lat: cy, lng: cx, degenerate: false };
}

function centroidOf(parsed) {
  if (parsed.kind === "point") return { lat: parsed.lat, lng: parsed.lng, degenerate: false };
  return polygonCentroid(parsed.vertices);
}

// Which 5x5-degree tile does a point fall in? Aligned to absolute integer
// degree lines (no CONUS-specific offset needed, unlike the meteorology
// unit's antimeridian-wraparound math -- CONUS lat/lon never wrap).
function tileForPoint(lat, lng, tileDeg = TILE_DEG) {
  const lat0 = Math.floor(lat / tileDeg) * tileDeg;
  const lon0 = Math.floor(lng / tileDeg) * tileDeg;
  return { lat0, lon0, key: `${lat0}_${lon0}` };
}

const TILE_CACHE = {};

async function loadManifest(baseUrl) {
  const res = await fetch(`${baseUrl}/manifest.json`);
  if (!res.ok) throw new Error(`Couldn't load tile manifest (HTTP ${res.status}).`);
  return res.json();
}

async function loadTile(baseUrl, manifest, lat0, lon0) {
  const key = `${lat0}_${lon0}`;
  if (TILE_CACHE[key]) return TILE_CACHE[key];
  const entry = manifest.tiles[key];
  if (!entry) return null; // outside the tiled CONUS coverage (e.g. ocean, or off the continent)
  const res = await fetch(`${baseUrl}/${entry.file}`);
  if (!res.ok) throw new Error(`Couldn't load weather tile ${key} (HTTP ${res.status}).`);
  const buf = await res.arrayBuffer();
  const ds = new DecompressionStream("gzip");
  const decompressedStream = new Response(buf).body.pipeThrough(ds);
  const decompressed = await new Response(decompressedStream).arrayBuffer();
  TILE_CACHE[key] = decompressed;
  return decompressed;
}

// Full pipeline: KML text -> centroid -> which tile -> that tile's raw bytes.
async function resolveFieldTile(kmlText, baseUrl) {
  const parsed = parseKML(kmlText);
  const centroid = centroidOf(parsed);
  const tile = tileForPoint(centroid.lat, centroid.lng);
  const manifest = await loadManifest(baseUrl);
  const bytes = await loadTile(baseUrl, manifest, tile.lat0, tile.lon0);
  return { parsed, centroid, tile, manifest, bytes };
}

// --- Weather tile decoding (real layout, fixed by the Colab export script
// that produced agricultural/prototypes' GitHub Release tiles, not guessed) ---
//
// Per tile file: cells in the exact order manifest.tiles[key].cells lists
// them; each cell's days in chronological order across manifest.years[0]
// through manifest.years[1] inclusive (real Gregorian leap days included,
// matching cycles_engine_validate.py's own 13,515-day validated record for
// 1980-2016); each day's fields in manifest.fields order; all little-endian
// int16, scaled per manifest.scale. This is the same field order the
// embedded engine's own ALL_WX already uses (see engine-demo.html's
// to_row()), so a decoded cell is a drop-in replacement for one of ALL_WX's
// years, no translation needed.

function isLeapYear(y) {
  return y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);
}

// [[year, doy], ...] for every real calendar day from y0-01-01 through
// y1-12-31 inclusive, in chronological order -- the same order the packer
// script iterated in when writing each cell's flat day sequence.
function allYearDoys(y0, y1) {
  const out = [];
  for (let y = y0; y <= y1; y++) {
    const n = isLeapYear(y) ? 366 : 365;
    for (let d = 1; d <= n; d++) out.push([y, d]);
  }
  return out;
}

// Decodes one cell out of a tile's decompressed bytes into
// {year: {doy: [field...]}}, matching ALL_WX's own shape exactly.
function decodeCellWeather(bytes, cellIndex, manifest, tileEntry) {
  const days = allYearDoys(manifest.years[0], manifest.years[1]);
  if (tileEntry && tileEntry.n_days != null && tileEntry.n_days !== days.length) {
    throw new Error(`Tile n_days (${tileEntry.n_days}) doesn't match the manifest's declared year range (${days.length} days) -- decoder/packer are out of sync.`);
  }
  const nFields = manifest.fields.length;
  const view = new Int16Array(bytes);
  const recordsPerCell = days.length * nFields;
  const offset = cellIndex * recordsPerCell;

  const wx = {};
  for (let i = 0; i < days.length; i++) {
    const [year, doy] = days[i];
    const values = new Array(nFields);
    for (let f = 0; f < nFields; f++) {
      values[f] = view[offset + i * nFields + f] * manifest.scale[manifest.fields[f]];
    }
    if (!wx[year]) wx[year] = {};
    wx[year][doy] = values;
  }
  return wx;
}

// Full pipeline: KML text -> centroid -> nearest real weather cell within
// its tile -> decoded {year: {doy: [values]}}, ready to hand to the
// embedded engine as ALL_WX. distanceDeg well above the tile's own
// resolution_deg means no real cell was nearby (shouldn't happen once a
// tile itself is found, since tiles are only built where real cells exist,
// but checked anyway rather than trusted blindly).
async function resolveFieldWeather(kmlText, baseUrl) {
  const parsed = parseKML(kmlText);
  const centroid = centroidOf(parsed);
  const tile = tileForPoint(centroid.lat, centroid.lng);
  const manifest = await loadManifest(baseUrl);
  const tileEntry = manifest.tiles[tile.key];
  if (!tileEntry) {
    return { parsed, centroid, tile, manifest, weather: null, cell: null, distanceDeg: Infinity };
  }
  const bytes = await loadTile(baseUrl, manifest, tile.lat0, tile.lon0);
  let bestIdx = 0, bestDist = Infinity;
  tileEntry.cells.forEach(([clat, clon], idx) => {
    const d = Math.hypot(clat - centroid.lat, clon - centroid.lng);
    if (d < bestDist) { bestDist = d; bestIdx = idx; }
  });
  const weather = decodeCellWeather(bytes, bestIdx, manifest, tileEntry);
  return { parsed, centroid, tile, manifest, weather, cell: tileEntry.cells[bestIdx], distanceDeg: bestDist };
}

// --- Soil lookup (STATSGO2, agricultural/prototypes/statsgo2_soil_grid.json.gz) ---
//
// Unlike the weather tiles above (still waiting on Matt's export), this data
// is real and already committed to the repo -- see CLAUDE.md's "STATSGO2
// soil export completed end to end" entry. It's a flat list of ~3044 grid
// cells at 0.5-degree resolution (cell-centered at .25/.75), each carrying
// the dominant STATSGO2 map-unit component's real horizon layers
// (thick in meters, clay/sand in %, soc in % -- same shape as
// run_validation.py's SOIL_LAYERS_RAW, so a resolved cell can be handed
// straight to make_layers()/saxton_rawls() with no translation).
//
// Deep horizons frequently have no organic-matter measurement in the source
// data (real SSURGO/STATSGO2 characteristic -- topsoil OM is measured far
// more often than subsoil OM is). DEFAULT_SUBSOIL_SOC_PCT is a disclosed
// stand-in for those nulls, not a real per-cell value -- chosen to sit in
// the same 0.17-0.27% range Rock Springs' own real deep layers already use
// in this codebase, not derived from this dataset itself.
const DEFAULT_SUBSOIL_SOC_PCT = 0.2;

// Small enough (3044 points) that a linear nearest-neighbor scan per lookup
// is fine -- this runs once per field selection, not in a hot loop.
function nearestSoilCell(lat, lng, grid) {
  let best = null, bestDist = Infinity;
  for (const cell of grid) {
    const dLat = cell.lat - lat, dLon = cell.lon - lng;
    const dist = Math.sqrt(dLat * dLat + dLon * dLon);
    if (dist < bestDist) { bestDist = dist; best = cell; }
  }
  return { cell: best, distanceDeg: bestDist };
}

// Converts a raw grid cell's layers into the exact SOIL_LAYERS_RAW shape
// used elsewhere in this codebase, filling null soc with the disclosed
// default above rather than leaving it null for saxton_rawls() to choke on.
function soilLayersForCell(cell) {
  return cell.layers.map((l) => ({
    thick: l.thick,
    clay: l.clay,
    sand: l.sand,
    soc: l.soc == null ? DEFAULT_SUBSOIL_SOC_PCT : l.soc,
  }));
}

async function loadSoilGrid(baseUrl) {
  const res = await fetch(`${baseUrl}/statsgo2_soil_grid.json.gz`);
  if (!res.ok) throw new Error(`Couldn't load soil grid (HTTP ${res.status}).`);
  const buf = await res.arrayBuffer();
  const ds = new DecompressionStream("gzip");
  const decompressedStream = new Response(buf).body.pipeThrough(ds);
  const text = await new Response(decompressedStream).text();
  return JSON.parse(text);
}

// Full pipeline: KML text -> centroid -> nearest real STATSGO2 grid cell ->
// SOIL_LAYERS_RAW-shaped layers ready for the engine. A distanceDeg well
// above the 0.5-degree grid spacing means the point fell outside real
// coverage (ocean, Great Lakes, just past the CONUS border) and the
// returned profile shouldn't be trusted -- callers should check it.
async function resolveFieldSoil(kmlText, baseUrl) {
  const parsed = parseKML(kmlText);
  const centroid = centroidOf(parsed);
  const grid = await loadSoilGrid(baseUrl);
  const { cell, distanceDeg } = nearestSoilCell(centroid.lat, centroid.lng, grid);
  const layers = soilLayersForCell(cell);
  return { parsed, centroid, cell, distanceDeg, layers };
}

if (typeof module !== "undefined") {
  module.exports = {
    parseKML, polygonCentroid, centroidOf, tileForPoint, loadManifest, loadTile, resolveFieldTile, TILE_DEG,
    nearestSoilCell, soilLayersForCell, loadSoilGrid, resolveFieldSoil, DEFAULT_SUBSOIL_SOC_PCT,
    isLeapYear, allYearDoys, decodeCellWeather, resolveFieldWeather,
  };
}
