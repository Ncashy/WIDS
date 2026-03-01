"""
preprocess_geo_data.py

Run this ONCE from your 01_raw_data directory to generate lightweight GeoJSON files
that Streamlit can load quickly. The source CSVs are 100s of MB; the output files
will be a few MB each.

Usage (from your widsdatathon/01_raw_data directory):
    python3 preprocess_geo_data.py

Outputs (written to 01_raw_data/processed/):
    evac_zones_active.geojson       — active evacuation zone polygons (~3-8 MB)
    fire_perimeters_approved.geojson — approved fire perimeter polygons (~5-15 MB)
    geo_events_summary.csv          — lightweight geo event lookup table

Requirements:
    pip3 install shapely --break-system-packages
"""

import pandas as pd
import json
import re
import os
import sys
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────
HERE       = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, "processed")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ══════════════════════════════════════════════════════════════════════
# WKT PARSER  (no geopandas required — pure Python + regex)
# ══════════════════════════════════════════════════════════════════════

def strip_srid(wkt):
    """Remove SRID=4326; prefix if present."""
    if wkt and isinstance(wkt, str):
        return re.sub(r'^SRID=\d+;', '', wkt.strip())
    return None

def wkt_polygon_to_coords(wkt):
    """
    Convert WKT POLYGON or MULTIPOLYGON to GeoJSON coordinate array.
    Returns (geojson_type, coordinates) or (None, None) on failure.
    """
    wkt = strip_srid(wkt)
    if not wkt:
        return None, None
    try:
        wkt = wkt.strip()
        if wkt.startswith("MULTIPOLYGON"):
            # Extract all polygon rings
            rings_str = wkt[len("MULTIPOLYGON"):].strip()
            # Remove outer parens of multipolygon
            rings_str = rings_str.strip("()")
            # Split individual polygons — each is ((ring1),(ring2)...)
            polys = []
            depth = 0
            current = ""
            for ch in rings_str:
                if ch == "(":
                    depth += 1
                    current += ch
                elif ch == ")":
                    depth -= 1
                    current += ch
                    if depth == 0:
                        polys.append(current.strip())
                        current = ""
                else:
                    current += ch

            coordinates = []
            for poly_str in polys:
                poly_str = poly_str.strip("()")
                rings = parse_rings(poly_str)
                if rings:
                    coordinates.append(rings)
            return "MultiPolygon", coordinates if coordinates else None

        elif wkt.startswith("POLYGON"):
            rings_str = wkt[len("POLYGON"):].strip().strip("()")
            rings = parse_rings(rings_str)
            return "Polygon", rings if rings else None

        else:
            return None, None
    except Exception:
        return None, None

def parse_rings(rings_str):
    """Parse one or more WKT rings into GeoJSON coordinate arrays."""
    rings = []
    depth = 0
    current = ""
    for ch in rings_str:
        if ch == "(":
            depth += 1
            if depth == 1:
                current = ""
            else:
                current += ch
        elif ch == ")":
            depth -= 1
            if depth == 0:
                coords = parse_coord_string(current)
                if coords:
                    rings.append(coords)
                current = ""
            else:
                current += ch
        else:
            current += ch
    # Handle case with no inner parens (single ring)
    if not rings and rings_str:
        coords = parse_coord_string(rings_str)
        if coords:
            rings.append(coords)
    return rings

def parse_coord_string(s):
    """Parse 'lon lat, lon lat, ...' into [[lon, lat], ...]"""
    coords = []
    for pair in s.strip().split(","):
        parts = pair.strip().split()
        if len(parts) >= 2:
            try:
                coords.append([float(parts[0]), float(parts[1])])
            except ValueError:
                pass
    return coords if len(coords) >= 3 else None

def row_to_feature(geom_type, coordinates, properties):
    """Wrap geometry + properties into a GeoJSON Feature dict."""
    if not coordinates:
        return None
    return {
        "type": "Feature",
        "geometry": {
            "type": geom_type,
            "coordinates": coordinates
        },
        "properties": properties
    }

def write_geojson(features, path):
    """Write a list of GeoJSON features to a .geojson file."""
    fc = {"type": "FeatureCollection", "features": [f for f in features if f]}
    with open(path, "w") as fp:
        json.dump(fc, fp, separators=(",", ":"))  # compact — no extra whitespace
    size_mb = os.path.getsize(path) / 1024 / 1024
    log(f"  Written: {path}  ({size_mb:.1f} MB, {len(fc['features']):,} features)")

# ══════════════════════════════════════════════════════════════════════
# 1. EVACUATION ZONES
# ══════════════════════════════════════════════════════════════════════

def process_evac_zones():
    src = os.path.join(HERE, "evac_zones_gis_evaczone.csv")
    if not os.path.exists(src):
        log(f"SKIP: {src} not found")
        return

    log(f"Loading evac zones CSV (~195 MB, may take 30-60 seconds)...")
    df = pd.read_csv(src, dtype=str, low_memory=False)
    log(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")

    # Keep active zones only (is_active == 'true')
    df_active = df[df['is_active'].str.lower() == 'true'].copy()
    log(f"  Active zones: {len(df_active):,} of {len(df):,}")

    # Drop rows with null geometry
    df_active = df_active[df_active['geom'].notna() & (df_active['geom'] != '')].copy()
    log(f"  Rows with geometry: {len(df_active):,}")

    features = []
    skipped  = 0
    for i, (_, row) in enumerate(df_active.iterrows()):
        if i % 5000 == 0:
            log(f"  Processing row {i:,} / {len(df_active):,}...")
        geom_type, coords = wkt_polygon_to_coords(row.get('geom', ''))
        if not geom_type or not coords:
            skipped += 1
            continue

        # Extract state from dataset_name e.g. "boulder-CO_US" → "CO"
        dataset = str(row.get('dataset_name', ''))
        state   = ""
        m = re.search(r'-([A-Z]{2})_US', dataset)
        if m:
            state = m.group(1)

        props = {
            "uid":             str(row.get('uid_v2', '')),
            "display_name":    str(row.get('display_name', '')),
            "dataset_name":    dataset,
            "state":           state,
            "external_status": str(row.get('external_status', 'Normal')),
            "is_active":       True,
            "region_id":       str(row.get('region_id', '')),
        }
        features.append(row_to_feature(geom_type, coords, props))

    log(f"  Parsed {len(features):,} features, skipped {skipped:,}")
    out = os.path.join(OUTPUT_DIR, "evac_zones_active.geojson")
    write_geojson(features, out)

# ══════════════════════════════════════════════════════════════════════
# 2. FIRE PERIMETERS
# ══════════════════════════════════════════════════════════════════════

def process_fire_perimeters():
    src = os.path.join(HERE, "fire_perimeters_gis_fireperimeter.csv")
    if not os.path.exists(src):
        log(f"SKIP: {src} not found")
        return

    log(f"Loading fire perimeters CSV (~381 MB, may take 60-90 seconds)...")

    # Read in chunks to manage memory
    chunk_size = 10000
    features   = []
    skipped    = 0
    total_rows = 0

    # First get column names
    sample = pd.read_csv(src, nrows=2, dtype=str)
    log(f"  Columns: {list(sample.columns)}")

    geom_col = None
    for candidate in ['geom', 'geometry', 'shape', 'wkt']:
        if candidate in sample.columns:
            geom_col = candidate
            break
    if not geom_col:
        # Try to find a column containing POLYGON
        for col in sample.columns:
            val = str(sample[col].iloc[0]) if len(sample) > 0 else ""
            if "POLYGON" in val.upper() or "SRID" in val:
                geom_col = col
                break

    if not geom_col:
        log(f"  ERROR: Could not identify geometry column. Columns: {list(sample.columns)}")
        return

    log(f"  Using geometry column: '{geom_col}'")

    for chunk in pd.read_csv(src, dtype=str, low_memory=False, chunksize=chunk_size):
        total_rows += len(chunk)

        # Filter to approved perimeters only
        if 'approval_status' in chunk.columns:
            chunk = chunk[chunk['approval_status'].str.lower() == 'approved']

        for _, row in chunk.iterrows():
            geom_wkt = row.get(geom_col, '')
            if not geom_wkt or pd.isna(geom_wkt):
                skipped += 1
                continue
            geom_type, coords = wkt_polygon_to_coords(str(geom_wkt))
            if not geom_type or not coords:
                skipped += 1
                continue

            props = {
                "geo_event_id":    str(row.get('geo_event_id', '')),
                "approval_status": str(row.get('approval_status', '')),
                "source":          str(row.get('source', '')),
                "date_created":    str(row.get('date_created', '')),
                "date_modified":   str(row.get('date_modified', '')),
            }
            # Add any name/fire_name column if present
            for name_col in ['name','fire_name','label','title']:
                if name_col in row.index:
                    props['name'] = str(row.get(name_col, ''))
                    break

            features.append(row_to_feature(geom_type, coords, props))

        if total_rows % 50000 == 0:
            log(f"  Processed {total_rows:,} rows so far, {len(features):,} features...")

    log(f"  Total rows: {total_rows:,}, features: {len(features):,}, skipped: {skipped:,}")
    out = os.path.join(OUTPUT_DIR, "fire_perimeters_approved.geojson")
    write_geojson(features, out)

# ══════════════════════════════════════════════════════════════════════
# 3. GEO EVENTS SUMMARY  (lightweight CSV lookup)
# ══════════════════════════════════════════════════════════════════════

def process_geo_events():
    src = os.path.join(HERE, "geo_events_geoevent.csv")
    if not os.path.exists(src):
        log(f"SKIP: {src} not found")
        return

    log(f"Loading geo events CSV...")
    df = pd.read_csv(src, dtype=str, low_memory=False)
    log(f"  Loaded {len(df):,} rows, columns: {list(df.columns)}")

    # Keep useful columns only
    keep = [c for c in ['id','geo_event_id','name','fire_name','state','county',
                        'start_date','end_date','is_active','acres','cause',
                        'latitude','longitude','dataset_name'] if c in df.columns]
    df_out = df[keep].copy() if keep else df.copy()

    out = os.path.join(OUTPUT_DIR, "geo_events_summary.csv")
    df_out.to_csv(out, index=False)
    size_mb = os.path.getsize(out) / 1024 / 1024
    log(f"  Written: {out}  ({size_mb:.1f} MB, {len(df_out):,} rows)")

# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    log("=== WiDS Datathon Geo Data Preprocessor ===")
    log(f"Source directory: {HERE}")
    log(f"Output directory: {OUTPUT_DIR}")
    log("")

    log("--- Step 1: Evacuation Zones ---")
    process_evac_zones()
    log("")

    log("--- Step 2: Fire Perimeters ---")
    process_fire_perimeters()
    log("")

    log("--- Step 3: Geo Events Summary ---")
    process_geo_events()
    log("")

    log("=== Done! ===")
    log("Next steps:")
    log("  1. Copy the .geojson files to your wids-caregiver-alert/src/ folder")
    log("  2. The dashboard will automatically load them for the map")