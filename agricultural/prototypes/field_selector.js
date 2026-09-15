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

// Full pipeline: KML text -> centroid -> which tile -> that tile's raw bytes
// (decoding the per-cell weather record out of the tile's binary layout is
// deliberately NOT included here, since that layout is fixed by whatever
// Matt's Colab export actually produces -- write that decoder once the real
// manifest exists, against real bytes, not a guessed layout).
async function resolveFieldTile(kmlText, baseUrl) {
  const parsed = parseKML(kmlText);
  const centroid = centroidOf(parsed);
  const tile = tileForPoint(centroid.lat, centroid.lng);
  const manifest = await loadManifest(baseUrl);
  const bytes = await loadTile(baseUrl, manifest, tile.lat0, tile.lon0);
  return { parsed, centroid, tile, manifest, bytes };
}

if (typeof module !== "undefined") {
  module.exports = { parseKML, polygonCentroid, centroidOf, tileForPoint, loadManifest, loadTile, resolveFieldTile, TILE_DEG };
}
