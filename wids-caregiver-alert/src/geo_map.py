"""
geo_map.py  —  49ers Intelligence Lab

Renders the wildfire evacuation map using real polygon data:
  - Evacuation zone boundaries (evac_zones_map.geojson)
  - Fire perimeters (fire_perimeters_approved.geojson)
  - Vulnerable population markers (from SVI data)

Place this file in wids-caregiver-alert/src/
The GeoJSON files go in wids-caregiver-alert/src/ as well (copy from 01_raw_data/processed/).
"""

import streamlit as st
import folium
import json
import os
import pandas as pd


_HERE = os.path.dirname(os.path.abspath(__file__))

# ── Status color mapping ──────────────────────────────────────────────
STATUS_COLORS = {
    "Evacuation Order":   "#FF0000",
    "Evacuation Warning": "#FF8C00",
    "Shelter in Place":   "#FFD700",
    "Warning":            "#FF8C00",
    "Watch":              "#FFD700",
    "Normal":             "#00AA44",
    "":                   "#888888",
}

STATUS_FILL_OPACITY = {
    "Evacuation Order":   0.55,
    "Evacuation Warning": 0.40,
    "Shelter in Place":   0.35,
    "Warning":            0.40,
    "Watch":              0.30,
    "Normal":             0.08,
    "":                   0.10,
}


def _geojson_path(filename):
    """Search for a GeoJSON file in src/ and nearby data dirs."""
    candidates = [
        os.path.join(_HERE, filename),
        os.path.join(_HERE, "..", "01_raw_data", "processed", filename),
        os.path.join(_HERE, "..", "..", "01_raw_data", "processed", filename),
        os.path.join(_HERE, "..", "..", "..", "01_raw_data", "processed", filename),
        os.path.join("01_raw_data", "processed", filename),
    ]
    for p in candidates:
        if os.path.exists(os.path.realpath(p)):
            return os.path.realpath(p)
    return None


@st.cache_data(show_spinner=False)
def load_evac_zones():
    """Load and cache evacuation zone GeoJSON."""
    path = _geojson_path("evac_zones_map.geojson")
    if not path:
        return None
    with open(path) as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_fire_perimeters():
    """Load and cache fire perimeter GeoJSON."""
    path = _geojson_path("fire_perimeters_approved.geojson")
    if not path:
        return None
    with open(path) as f:
        return json.load(f)


def _classify_status(status):
    """
    Map raw status strings from GeoJSON to one of:
    'order', 'warning', 'watch', 'normal'
    """
    s = str(status).lower().strip()

    # Inactive / lifted / no order → treat as normal
    if any(x in s for x in ['inactive', 'lifted', 'liftd', 'no evacuation',
                              'no order', 'no status', 'nan', '00', '0',
                              'normal', 'monitor']):
        return 'normal'

    # Evacuation Orders → red
    if any(x in s for x in ['order', 'mandatory', 'go now', 'level 3']):
        return 'order'

    # Evacuation Warnings → orange
    if any(x in s for x in ['warning', 'warn', 'level 2', 'be set']):
        return 'warning'

    # Watch / Shelter / Pre-Evacuation → yellow
    if any(x in s for x in ['watch', 'shelter', 'advisory', 'ready',
                              'pre-evacuation', 'pre evacuation',
                              'level 1', 'be ready']):
        return 'watch'

    return 'normal'


def _status_color(status):
    kind = _classify_status(status)
    return {'order': '#FF0000', 'warning': '#FF8C00',
            'watch': '#FFD700', 'normal': '#00AA44'}.get(kind, '#888888')


def _status_opacity(status):
    kind = _classify_status(status)
    return {'order': 0.55, 'warning': 0.40,
            'watch': 0.30, 'normal': 0.08}.get(kind, 0.10)


def build_evacuation_map(
    vulnerable_populations: dict,
    fire_data: pd.DataFrame,
    show_normal_zones: bool = False,
    selected_state: str = "All",
    height: int = 550,
) -> folium.Map:
    """
    Build and return a Folium map with:
      - Real evacuation zone polygons (colored by status)
      - Real fire perimeter polygons
      - Vulnerable population markers (SVI data)
    """
    m = folium.Map(
        location=[39.5, -98.5],
        zoom_start=4,
        tiles="CartoDB dark_matter",
    )

    # ── Legend ────────────────────────────────────────────────────────
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:rgba(20,20,30,0.92);padding:12px 16px;
                border-radius:8px;border:1px solid #444;font-size:12px;color:#eee;">
      <b style="font-size:13px;">Evacuation Status</b><br>
      <span style="color:#FF0000;">&#9632;</span> Evacuation Order<br>
      <span style="color:#FF8C00;">&#9632;</span> Evacuation Warning<br>
      <span style="color:#FFD700;">&#9632;</span> Watch / Shelter in Place<br>
      <span style="color:#FF6633;">&#9632;</span> Fire Perimeter<br>
      <span style="color:#4B9FFF;">&#9632;</span> Vulnerable Population
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # ── Fire perimeters ───────────────────────────────────────────────
    fire_perim_data = load_fire_perimeters()
    if fire_perim_data:
        perim_group = folium.FeatureGroup(name="Fire Perimeters", show=True)
        for feat in fire_perim_data.get("features", []):
            if not feat or not feat.get("geometry"):
                continue
            props = feat.get("properties", {})
            name  = props.get("name") or props.get("source_incident_name") or "Fire Perimeter"
            date  = str(props.get("date_modified", ""))[:10]
            folium.GeoJson(
                feat,
                style_function=lambda x: {
                    "color":       "#FF6633",
                    "weight":      2,
                    "fillColor":   "#FF4400",
                    "fillOpacity": 0.30,
                },
                tooltip=folium.Tooltip(f"<b>{name}</b><br>Updated: {date}"),
            ).add_to(perim_group)
        perim_group.add_to(m)

    # ── Evacuation zones ──────────────────────────────────────────────
    evac_data = load_evac_zones()
    if evac_data:
        order_group   = folium.FeatureGroup(name="Evacuation Orders",   show=True)
        warning_group = folium.FeatureGroup(name="Evacuation Warnings", show=True)
        watch_group   = folium.FeatureGroup(name="Watch / Shelter",     show=True)
        normal_group  = folium.FeatureGroup(name="Normal Zones",        show=show_normal_zones)

        order_count = warning_count = watch_count = normal_count = 0

        for feat in evac_data.get("features", []):
            if not feat or not feat.get("geometry"):
                continue
            props  = feat.get("properties", {})
            status = str(props.get("status", "Normal"))
            state  = str(props.get("state", ""))
            name   = props.get("name", "")
            dataset= props.get("dataset", "")

            # State filter
            if selected_state != "All" and state != selected_state:
                continue

            kind = _classify_status(status)
            is_normal = (kind == 'normal')

            # Skip normal zones when hidden to avoid serializing ~30k polygons
            if is_normal:
                normal_count += 1
                if not show_normal_zones:
                    continue

            color   = _status_color(status)
            opacity = _status_opacity(status)

            geo_layer = folium.GeoJson(
                feat,
                style_function=lambda x, c=color, o=opacity: {
                    "color":       c,
                    "weight":      1.5 if o > 0.2 else 0.5,
                    "fillColor":   c,
                    "fillOpacity": o,
                },
                tooltip=folium.Tooltip(
                    f"<b>{name or dataset}</b><br>"
                    f"Status: <b style='color:{color}'>{status}</b><br>"
                    f"State: {state}"
                ),
            )

            if kind == 'order':
                geo_layer.add_to(order_group);   order_count += 1
            elif kind == 'warning':
                geo_layer.add_to(warning_group); warning_count += 1
            elif kind == 'watch':
                geo_layer.add_to(watch_group);   watch_count += 1
            else:
                geo_layer.add_to(normal_group)

        normal_group.add_to(m)
        watch_group.add_to(m)
        warning_group.add_to(m)
        order_group.add_to(m)   # orders render on top

    # ── Vulnerable population markers ─────────────────────────────────
    if vulnerable_populations:
        vp_group = folium.FeatureGroup(name="Vulnerable Populations", show=False)
        for loc_name, data in list(vulnerable_populations.items())[:300]:
            svi   = data.get("svi_score", 0)
            count = data.get("vulnerable_count", 0)
            radius = 4 + svi * 8

            folium.CircleMarker(
                location=[data["lat"], data["lon"]],
                radius=radius,
                color="#4B9FFF",
                fill=True,
                fillColor="#4B9FFF",
                fillOpacity=0.6,
                weight=1,
                tooltip=folium.Tooltip(
                    f"<b>{loc_name}</b><br>"
                    f"Vulnerable: {count:,}<br>"
                    f"SVI Score: {svi:.3f}"
                ),
            ).add_to(vp_group)
        vp_group.add_to(m)

    # ── Live NASA fire hotspots ───────────────────────────────────────
    if fire_data is not None and len(fire_data) > 0 and "latitude" in fire_data.columns:
        hotspot_group = folium.FeatureGroup(name="Live Fire Hotspots", show=False)
        display = fire_data.nlargest(150, "acres") if "acres" in fire_data.columns else fire_data.head(150)
        for _, fire in display.iterrows():
            acres = fire.get("acres", 0)
            folium.CircleMarker(
                location=[fire["latitude"], fire["longitude"]],
                radius=5,
                color="#FF2200",
                fill=True,
                fillColor="#FF6600",
                fillOpacity=0.85,
                weight=1,
                tooltip=folium.Tooltip(
                    f"<b>{fire.get('fire_name','Active Fire')}</b><br>"
                    f"{acres:,.0f} acres"
                ),
            ).add_to(hotspot_group)
        hotspot_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def render_map_with_controls(vulnerable_populations, fire_data, height=550):
    """
    Streamlit wrapper — renders state filter + map with loading indicator.
    Call this from your dashboard pages.
    """
    evac_data = load_evac_zones()

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        states = ["All"]
        if evac_data:
            state_set = set()
            for feat in evac_data.get("features", []):
                s = feat.get("properties", {}).get("state", "")
                if s:
                    state_set.add(s)
            states = ["All"] + sorted(state_set)
        selected_state = st.selectbox("Filter by State", states, key="map_state_filter")

    with col2:
        show_normal = st.checkbox("Show Normal Zones", value=False, key="map_show_normal",
                                  help="Normal zones are shown faintly — hiding them speeds up rendering")

    with col3:
        if evac_data:
            n_features = len(evac_data.get("features", []))
            non_normal = sum(
                1 for f in evac_data.get("features", [])
                if f and "normal" not in str(f.get("properties", {}).get("status", "")).lower()
            )
            st.caption(f"{n_features:,} evacuation zones loaded  ·  "
                       f"{non_normal:,} active  ·  "
                       f"Data: Genasys Protect / WiDS 2025")
        else:
            st.caption("⚠️ GeoJSON not found — copy evac_zones_map.geojson to src/")

    if not evac_data and not load_fire_perimeters():
        st.warning(
            "Real polygon data not found. Copy these files to your `src/` folder:\n"
            "- `01_raw_data/processed/evac_zones_map.geojson`\n"
            "- `01_raw_data/processed/fire_perimeters_approved.geojson`"
        )

    # Cache-clear button (safe here, inside a function)
    if st.button("🔄 Clear Map Cache", key="clear_map_cache"):
        load_evac_zones.clear()
        load_fire_perimeters.clear()
        st.rerun()

    with st.spinner("Rendering map..."):
        m = build_evacuation_map(
            vulnerable_populations=vulnerable_populations,
            fire_data=fire_data,
            show_normal_zones=show_normal,
            selected_state=selected_state,
            height=height,
        )

    from streamlit_folium import st_folium
    st_folium(m, width=None, height=height, returned_objects=[])