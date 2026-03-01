"""
caregiver_dashboard_FINAL.py  —  patched

Changes
───────
1  Logo: the via.placeholder.com image (always broken) is replaced with an
   inline SVG rendered via st.markdown.  When the team's Canva logo is ready
   just drop the PNG into src/ and swap in st.image("logo.png").
2  SVI path resolution: all relative paths are now anchored to the directory
   of THIS file (via __file__), so the app works no matter where the user
   runs `streamlit run` from.  Added the full repo layout variants.
3  Emoji pass: removed decorative emoji clusters in sidebar and headers;
   kept single-purpose warning/success icons only.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
import os

# ── resolve THIS file's directory so all relative paths work ─────────
_HERE = os.path.dirname(os.path.abspath(__file__))

# Import fire data integration
from fire_data_integration import get_all_us_fires, get_fire_statistics, find_nearby_fires

# Import evacuation routes
try:
    from evacuation_routes import generate_evacuation_routes_for_alerts, calculate_evacuation_plan
    EVACUATION_AVAILABLE = True
except Exception:
    EVACUATION_AVAILABLE = False

# Import OSM routing (optional - requires network)
try:
    from osm_routing import get_real_driving_route, calculate_evacuation_route_osm
    OSM_ROUTING_AVAILABLE = True
except Exception:
    OSM_ROUTING_AVAILABLE = False

# Import evacuation planner page
try:
    from evacuation_planner_page import render_evacuation_planner_page
    PLANNER_AVAILABLE = True
except Exception:
    PLANNER_AVAILABLE = False

# Import directions & navigation page
try:
    from directions_page import render_directions_page
    DIRECTIONS_AVAILABLE = True
except Exception:
    DIRECTIONS_AVAILABLE = False

# ── page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Wildfire Caregiver Alert System",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .risk-high {
        background-color: #FF4B4B;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        font-weight: bold;
    }
    .risk-medium {
        background-color: #FFA500;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        font-weight: bold;
    }
    .risk-low {
        background-color: #00CC00;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# DATA LOADERS
# ══════════════════════════════════════════════════════════════════════

@st.cache_data
def load_exact_county_coordinates():
    """Load county centroids from Census file."""
    candidates = [
        os.path.join(_HERE, "..", "..", "..", "wids-caregiver-alert", "data", "CenPop2020_Mean_CO.txt"),
        os.path.join(_HERE, "..", "data", "CenPop2020_Mean_CO.txt"),
        os.path.join(_HERE, "..", "..", "wids-caregiver-alert", "data", "CenPop2020_Mean_CO.txt"),
        os.path.join(_HERE, "data", "CenPop2020_Mean_CO.txt"),
        os.path.join("wids-caregiver-alert", "data", "CenPop2020_Mean_CO.txt"),
        os.path.join("data", "CenPop2020_Mean_CO.txt"),
    ]
    candidates = [os.path.realpath(c) for c in candidates]

    census_path = None
    for p in candidates:
        if os.path.exists(p):
            census_path = p
            break

    if not census_path:
        st.sidebar.warning("County centroids file not found.  Falling back to state centres.")
        return None

    try:
        df = pd.read_csv(census_path, dtype={"STATEFP": str, "COUNTYFP": str})
        st.sidebar.info(f"Loaded {len(df)} counties from Census file.")
        coords = {}
        for _, row in df.iterrows():
            fips = str(row["STATEFP"]).zfill(2) + str(row["COUNTYFP"]).zfill(3)
            coords[fips] = (float(row["LATITUDE"]), float(row["LONGITUDE"]))
        st.sidebar.success(f"Exact coordinates: {len(coords)} counties")
        return coords
    except Exception as e:
        st.sidebar.warning(f"Census data error: {e}")
        return None


@st.cache_data
def load_state_coordinates():
    return {
        '01': (32.806671, -86.791130), '02': (61.370716, -152.404419), '04': (33.729759, -111.431221),
        '05': (34.969704, -92.373123), '06': (36.116203, -119.681564), '08': (39.059811, -105.311104),
        '09': (41.597782, -72.755371), '10': (39.318523, -75.507141), '12': (27.766279, -81.686783),
        '13': (33.040619, -83.643074), '15': (21.094318, -157.498337), '16': (44.240459, -114.478828),
        '17': (40.349457, -88.986137), '18': (39.849426, -86.258278), '19': (42.011539, -93.210526),
        '20': (38.526600, -96.726486), '21': (37.668140, -84.670067), '22': (31.169546, -91.867805),
        '23': (44.693947, -69.381927), '24': (39.063946, -76.802101), '25': (42.230171, -71.530106),
        '26': (43.326618, -84.536095), '27': (45.694454, -93.900192), '28': (32.741646, -89.678696),
        '29': (38.456085, -92.288368), '30': (46.921925, -110.454353), '31': (41.125370, -98.268082),
        '32': (38.313515, -117.055374), '33': (43.452492, -71.563896), '34': (40.298904, -74.521011),
        '35': (34.840515, -106.248482), '36': (42.165726, -74.948051), '37': (35.630066, -79.806419),
        '38': (47.528912, -99.784012), '39': (40.388783, -82.764915), '40': (35.565342, -96.928917),
        '41': (44.572021, -122.070938), '42': (40.590752, -77.209755), '44': (41.680893, -71.511780),
        '45': (33.856892, -80.945007), '46': (44.299782, -99.438828), '47': (35.747845, -86.692345),
        '48': (31.054487, -97.563461), '49': (40.150032, -111.862434), '50': (44.045876, -72.710686),
        '51': (37.769337, -78.169968), '53': (47.400902, -121.490494), '54': (38.491226, -80.954453),
        '55': (44.268543, -89.616508), '56': (42.755966, -107.302490), '11': (38.897438, -77.026817),
    }


@st.cache_data
def load_vulnerable_populations():
    """
    Load vulnerable populations from CDC SVI data.
    Paths anchored to _HERE so this works from any CWD.
    """
    candidates = [
        # three levels up from src/ → repo root (Streamlit Cloud layout)
        os.path.join(_HERE, "..", "..", "..", "01_raw_data", "external", "SVI_2022_US_county.csv"),
        # two levels up from src/ → repo root (local layout)
        os.path.join(_HERE, "..", "..", "01_raw_data", "external", "SVI_2022_US_county.csv"),
        # one level up from src/ → wids-caregiver-alert root
        os.path.join(_HERE, "..", "01_raw_data", "external", "SVI_2022_US_county.csv"),
        # if run from repo root directly
        os.path.join("01_raw_data", "external", "SVI_2022_US_county.csv"),
        # inside data/ subfolder
        os.path.join(_HERE, "..", "data", "SVI_2022_US_county.csv"),
        os.path.join("data", "SVI_2022_US_county.csv"),
    ]
    # realpath every candidate so ".." segments resolve fully before exists()
    candidates = [os.path.realpath(c) for c in candidates]

    svi_path = None
    for p in candidates:
        if os.path.exists(p):
            svi_path = p
            st.sidebar.success("Found SVI data.")
            break

    if svi_path is None:
        st.sidebar.warning(
            "SVI CSV not found at expected paths.  "
            "Searched:\n" + "\n".join(f"  {c}" for c in candidates)
        )
        # Return a richer fallback than before — still only 3 entries, but
        # with a clear note so devs know to fix the path.
        return {
            'Los Angeles County, CA': {'lat': 34.0522, 'lon': -118.2437, 'vulnerable_count': 523, 'svi_score': 0.95},
            'Maricopa County, AZ':    {'lat': 33.4484, 'lon': -112.0740, 'vulnerable_count': 456, 'svi_score': 0.89},
            'King County, WA':        {'lat': 47.6062, 'lon': -122.3321, 'vulnerable_count': 412, 'svi_score': 0.82},
            'Harris County, TX':      {'lat': 29.7604, 'lon': -95.3698,  'vulnerable_count': 498, 'svi_score': 0.91},
            'Cook County, IL':        {'lat': 41.8781, 'lon': -87.6298,  'vulnerable_count': 445, 'svi_score': 0.86},
            'Miami-Dade County, FL':  {'lat': 25.7617, 'lon': -80.1918,  'vulnerable_count': 510, 'svi_score': 0.93},
        }

    try:
        svi = pd.read_csv(svi_path)
        vulnerable = svi[svi['RPL_THEMES'] >= 0.75].copy()
        st.sidebar.info(f"{len(vulnerable)} high-vulnerability counties found.")

        exact_coords = load_exact_county_coordinates()

        if exact_coords:
            def get_coords(fips):
                fips_str = str(int(fips)).zfill(5)
                return exact_coords.get(fips_str, (39.8283, -98.5795))
            vulnerable['lat'] = vulnerable['FIPS'].apply(lambda x: get_coords(x)[0])
            vulnerable['lon'] = vulnerable['FIPS'].apply(lambda x: get_coords(x)[1])
            st.sidebar.success("Using exact county coordinates.")
        else:
            state_coords = load_state_coordinates()
            def get_state_coords(fips):
                try:
                    state_fips = str(int(fips))[:2].zfill(2)
                    return state_coords.get(state_fips, (39.8283, -98.5795))
                except Exception:
                    return (39.8283, -98.5795)
            vulnerable['lat'] = vulnerable['FIPS'].apply(lambda x: get_state_coords(x)[0])
            vulnerable['lon'] = vulnerable['FIPS'].apply(lambda x: get_state_coords(x)[1])
            st.sidebar.info("Using state-level coordinates (county centroids not available).")

        vulnerable_pops = {}
        for _, row in vulnerable.iterrows():
            location_key = f"{row['COUNTY']}, {row['STATE']}"
            vulnerable_pops[location_key] = {
                'lat': row['lat'],
                'lon': row['lon'],
                'vulnerable_count': max(int(row.get('E_AGE65', 0) + row.get('E_POV150', 0) * 0.5), 100),
                'svi_score': float(row['RPL_THEMES'])
            }

        df = pd.DataFrame.from_dict(vulnerable_pops, orient='index')
        df = df.sort_values('svi_score', ascending=False).head(200)
        st.sidebar.success(f"{len(df)} counties loaded.")
        return df.to_dict('index')

    except Exception as e:
        st.sidebar.error(f"Error loading SVI: {e}")
        return {'Los Angeles County, CA': {'lat': 34.0522, 'lon': -118.2437, 'vulnerable_count': 523, 'svi_score': 0.95}}


@st.cache_data
def load_wids_analysis_data():
    candidates = [
        os.path.join(_HERE, "..", "..", "..", "01_raw_data", "processed", "fire_events_with_svi_and_delays.csv"),
        os.path.join(_HERE, "..", "..", "01_raw_data", "processed", "fire_events_with_svi_and_delays.csv"),
        os.path.join(_HERE, "..", "01_raw_data", "processed", "fire_events_with_svi_and_delays.csv"),
        os.path.join("01_raw_data", "processed", "fire_events_with_svi_and_delays.csv"),
    ]
    candidates = [os.path.realpath(c) for c in candidates]
    for p in candidates:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p)
                st.sidebar.success(f"Loaded WiDS analysis: {len(df)} fire events.")
                return df
            except Exception as e:
                st.sidebar.warning(f"Could not load WiDS data: {e}")
                return None
    return None


# ══════════════════════════════════════════════════════════════════════
# HEADER  —  inline SVG logo replaces the broken placeholder image.
#            Drop a logo.png into src/ and swap this line:
#              st.image(os.path.join(_HERE, "logo.png"), use_container_width=True)
# ══════════════════════════════════════════════════════════════════════

LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 90" width="320" height="90">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e"/>
      <stop offset="100%" style="stop-color:#16213e"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#e94560"/>
      <stop offset="100%" style="stop-color:#f5a623"/>
    </linearGradient>
  </defs>
  <!-- background -->
  <rect width="320" height="90" rx="12" fill="url(#bg)"/>
  <!-- top accent bar -->
  <rect y="0" width="320" height="4" rx="2" fill="url(#accent)"/>
  <!-- flame icon (simplified) -->
  <g transform="translate(22,18)">
    <ellipse cx="14" cy="36" rx="10" ry="12" fill="#e94560" opacity="0.9"/>
    <ellipse cx="14" cy="30" rx="7" ry="10" fill="#f5a623"/>
    <ellipse cx="14" cy="24" rx="4" ry="6"  fill="#fff" opacity="0.85"/>
  </g>
  <!-- primary text -->
  <text x="54" y="38" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#ffffff">49ers Intelligence Lab</text>
  <!-- sub text -->
  <text x="54" y="60" font-family="Arial, sans-serif" font-size="11" fill="#aaaaaa">Wildfire Caregiver Alert System</text>
  <!-- WiDS badge -->
  <rect x="220" y="52" width="78" height="24" rx="12" fill="#e94560" opacity="0.85"/>
  <text x="259" y="69" font-family="Arial, sans-serif" font-size="12" font-weight="bold" fill="#fff" text-anchor="middle">WiDS 2025</text>
</svg>
"""


# ══════════════════════════════════════════════════════════════════════
# PAGE LAYOUT
# ══════════════════════════════════════════════════════════════════════

# Load data
vulnerable_populations = load_vulnerable_populations()
wids_data = load_wids_analysis_data()

# ── sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    # Inline SVG logo — no external image request, always renders
    st.markdown(LOGO_SVG, unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["Dashboard", "Evacuation Planner", "Directions & Navigation", "Equity Analysis", "Risk Calculator", "Impact Projection", "About"]
    )

    st.markdown("---")
    st.markdown("### Live Fire Data")

    @st.cache_data(ttl=300)
    def load_fire_data():
        return get_all_us_fires(days=1)

    try:
        fire_data = load_fire_data()
        fire_stats = get_fire_statistics(fire_data)
        if len(fire_data) > 0:
            st.metric("Active Fires (24h)", fire_stats['total_fires'])
            st.metric("Named Fires",        fire_stats['named_fires'])
            st.metric("Total Acres",        f"{fire_stats['total_acres']:,.0f}")
        else:
            st.warning("No active fires")
            fire_data = pd.DataFrame()
    except Exception:
        st.error("Fire data unavailable")
        fire_data = pd.DataFrame()

    st.markdown("---")
    st.markdown("### Monitored Areas")
    st.metric("Vulnerable Counties",  len(vulnerable_populations))
    total_vuln = sum(loc['vulnerable_count'] for loc in vulnerable_populations.values())
    st.metric("At-Risk Individuals", f"{total_vuln:,}")


# ══════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════
if page == "Dashboard":

    st.markdown('<h1 class="main-header">Wildfire Caregiver Alert System</h1>', unsafe_allow_html=True)
    st.markdown("### Reducing Evacuation Delays for Vulnerable Populations Through Data-Driven Alerts")

    st.info(f"Live: {len(fire_data)} fires  ·  {len(vulnerable_populations)} vulnerable counties monitored")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Caregivers", "2,847", "+127")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Alert Speed", "12 min", "-8 min")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Lives Protected", "5,694", "+358")
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Success Rate", "94.2%", "+11%")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    col_map, col_alerts = st.columns([2, 1])

    with col_map:
        st.subheader("Fires & Vulnerable Populations")
        m = folium.Map(location=[39.8283, -98.5795], zoom_start=4)

        if len(fire_data) > 0:
            display_fires = fire_data.nlargest(100, 'acres') if 'acres' in fire_data.columns else fire_data.head(100)
            for _, fire in display_fires.iterrows():
                acres  = fire.get('acres', 0)
                radius = min(max(acres * 50, 20000), 100000)
                folium.Circle(
                    location=[fire['latitude'], fire['longitude']],
                    radius=radius, color='red', fill=True,
                    fillColor='orange', fillOpacity=0.4,
                    popup=f"<b>{fire.get('fire_name')}</b><br>{acres:,.0f} acres"
                ).add_to(m)

            st.caption(f"Fires: {len(display_fires)} of {len(fire_data)}")

            alerts = find_nearby_fires(fire_data, vulnerable_populations, radius_km=80)
            if alerts:
                alerted_locations = set(a['Location'] for a in alerts)
                for loc_name in alerted_locations:
                    if loc_name in vulnerable_populations:
                        data = vulnerable_populations[loc_name]
                        fire_count = sum(1 for a in alerts if a['Location'] == loc_name)
                        folium.Marker(
                            location=[data['lat'], data['lon']],
                            popup=(
                                f"<b>{loc_name}</b><br>"
                                f"{data['vulnerable_count']:,} vulnerable<br>"
                                f"SVI: {data.get('svi_score', 0):.2f}<br>"
                                f"{fire_count} fires nearby"
                            ),
                            icon=folium.Icon(color='blue', icon='users', prefix='fa'),
                            tooltip=f"{fire_count} fires within 50 mi"
                        ).add_to(m)
                st.caption(f"Showing {len(alerted_locations)} counties with fires nearby (within 50 miles)")
            else:
                st.caption("No vulnerable counties with nearby fires.")
        else:
            st.info("No active fires to display.")

        st_folium(m, width=700, height=500)

    with col_alerts:
        st.subheader("Proximity Alerts")
        if len(fire_data) > 0:
            alerts = find_nearby_fires(fire_data, vulnerable_populations, radius_km=80)
            if alerts:
                df_alerts = pd.DataFrame(alerts)[['Location', 'Fire_Name', 'Distance_mi', 'Fire_Acres']].head(20)
                df_alerts.columns = ['Location', 'Fire', 'Dist (mi)', 'Acres']
                st.warning(f"{len(alerts)} ALERTS")
                st.dataframe(df_alerts, hide_index=True)
                if len(alerts) > 20:
                    st.caption(f"Top 20 of {len(alerts)} alerts")

                if EVACUATION_AVAILABLE and len(alerts) > 0:
                    st.markdown("---")
                    st.subheader("Evacuation Routes")
                    if OSM_ROUTING_AVAILABLE:
                        st.caption("Using OpenStreetMap real road routing")
                    else:
                        st.caption("Using estimated routes (straight-line + highways)")
                    try:
                        evac_plans = generate_evacuation_routes_for_alerts(
                            fire_data, vulnerable_populations, alerts[:5]
                        )
                        for plan in evac_plans:
                            urgency_label = {"HIGH": "[HIGH]", "MEDIUM": "[MED]", "LOW": "[LOW]"}.get(plan['urgency'], "")
                            highway_dist  = plan.get('highway_distance_mi')
                            highway_str   = f"{highway_dist:.1f} mi" if highway_dist else "N/A"
                            safe_zone_dist= plan.get('safe_zone_distance_mi')
                            safe_zone_str = f"{safe_zone_dist:.1f} mi" if safe_zone_dist else "N/A"

                            with st.expander(f"{urgency_label} {plan['location'][:30]}", expanded=(plan['urgency']=='HIGH')):
                                st.markdown(
                                    f"**Fire:** {plan['fire_name']}  \n"
                                    f"**Distance:** {plan['fire_distance_mi']:.1f} mi  |  **Urgency:** {plan['urgency']}\n\n"
                                    f"Evacuate: {plan['evacuation_direction']}  \n"
                                    f"Highway: {plan['nearest_highway']} ({highway_str})  \n"
                                    f"Safe Zone: {plan['safe_zone']} ({safe_zone_str})  \n"
                                    f"Total: ~{plan['total_distance_mi']:.0f} mi"
                                )
                    except Exception as e:
                        st.error(f"Route calculation error: {e}")
            else:
                st.success("No alerts.")

        st.markdown("---")
        st.subheader("Emergency")
        st.info("**Fire:** (704) 555-0100\n**Evacuation:** (704) 555-0200\n**911:** Emergency")


# ══════════════════════════════════════════════════════════════════════
# EVACUATION PLANNER
# ══════════════════════════════════════════════════════════════════════
elif page == "Evacuation Planner":
    if PLANNER_AVAILABLE:
        render_evacuation_planner_page(fire_data, vulnerable_populations)
    else:
        st.error("Evacuation Planner module not available.  Ensure evacuation_planner_page.py is in src/.")


# ══════════════════════════════════════════════════════════════════════
# DIRECTIONS & NAVIGATION
# ══════════════════════════════════════════════════════════════════════
elif page == "Directions & Navigation":
    if DIRECTIONS_AVAILABLE:
        render_directions_page(fire_data, vulnerable_populations)
    else:
        st.error("Directions module not available.  Ensure directions_page.py is in src/.")


# ══════════════════════════════════════════════════════════════════════
# EQUITY ANALYSIS
# ══════════════════════════════════════════════════════════════════════
elif page == "Equity Analysis":

    if wids_data is not None:
        st.success(f"Using WiDS Analysis Data ({len(wids_data)} events)")
        if 'evacuation_delay_hours' in wids_data.columns:
            st.subheader("Actual Evacuation Delays from WiDS Dataset")
            fig = px.histogram(wids_data, x='evacuation_delay_hours', nbins=50,
                               title="Distribution of Evacuation Delays")
            st.plotly_chart(fig)
            st.metric("Mean Delay",   f"{wids_data['evacuation_delay_hours'].mean():.2f} hours")
            st.metric("Median Delay", f"{wids_data['evacuation_delay_hours'].median():.2f} hours")
    else:
        st.info("Using simulated data (WiDS dataset not loaded).")

    st.header("Evacuation Equity Analysis")

    np.random.seed(42)
    vulnerable_delays     = np.random.gamma(3, 2, 1000)
    non_vulnerable_delays = np.random.gamma(2, 1.5, 1000)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Time Distribution")
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=vulnerable_delays,     name='Vulnerable',     marker_color='#FF4B4B', opacity=0.7))
        fig.add_trace(go.Histogram(x=non_vulnerable_delays, name='Non-Vulnerable', marker_color='#4B4BFF', opacity=0.7))
        fig.update_layout(barmode='overlay', xaxis_title='Hours', yaxis_title='Frequency', height=400)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Statistics")
        vuln_mean     = vulnerable_delays.mean()
        non_vuln_mean = non_vulnerable_delays.mean()
        diff          = vuln_mean - non_vuln_mean
        st.metric("Vulnerable Avg",     f"{vuln_mean:.2f}h")
        st.metric("Non-Vulnerable Avg", f"{non_vuln_mean:.2f}h")
        st.metric("Disparity",          f"{diff:.2f}h", delta=f"{diff/non_vuln_mean*100:.1f}%", delta_color="inverse")


# ══════════════════════════════════════════════════════════════════════
# RISK CALCULATOR
# ══════════════════════════════════════════════════════════════════════
elif page == "Risk Calculator":
    st.header("Risk Calculator")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Input")
        distance   = st.slider("Distance to fire (mi)", 0, 50, 15)
        age        = st.number_input("Age", 0, 120, 72)
        mobility   = st.checkbox("Mobility issues")
        chronic    = st.checkbox("Chronic illness")
        low_income = st.checkbox("Low income")
        alone      = st.checkbox("Lives alone")
        no_vehicle = st.checkbox("No vehicle")
    with col2:
        st.subheader("Result")
        score  = max(0, (age - 65) / 35 * 30)
        score += 20 if mobility   else 0
        score += 15 if chronic    else 0
        score += 10 if low_income else 0
        score += 10 if alone      else 0
        score += 10 if no_vehicle else 0
        score += max(0, (50 - distance) / 50 * 30)
        score  = min(100, score)

        if score >= 70:
            st.markdown(f'<div class="risk-high">HIGH RISK<br>Score: {score:.0f}/100</div>', unsafe_allow_html=True)
        elif score >= 40:
            st.markdown(f'<div class="risk-medium">MEDIUM RISK<br>Score: {score:.0f}/100</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="risk-low">LOW RISK<br>Score: {score:.0f}/100</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# IMPACT PROJECTION
# ══════════════════════════════════════════════════════════════════════
elif page == "Impact Projection":
    st.info("Data Source: WiDS Datathon 2025 Competition Dataset (Impact Modeling)")
    st.header("Projected Impact of Caregiver Alert System")

    col1, col2, col3 = st.columns(3)
    with col1:
        time_reduction  = st.slider("Avg Time Reduction (hours)", 0.5, 5.0, 2.0, 0.5)
    with col2:
        adoption_rate   = st.slider("Caregiver Adoption Rate (%)", 10, 100, 65, 5)
    with col3:
        population_size = st.number_input("Vulnerable Population Size", 1000, 100000, 10000, 1000)

    current_avg_delay      = 6.8
    reduced_avg_delay      = max(0, current_avg_delay - time_reduction)
    critical_threshold     = 6.0
    current_critical_pct   = 0.45
    reduced_critical_pct   = max(0, current_critical_pct - (time_reduction / current_avg_delay) * current_critical_pct)
    lives_protected        = int(population_size * (adoption_rate / 100) * (current_critical_pct - reduced_critical_pct))

    st.markdown("---")
    st.subheader("Projected Outcomes")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lives Protected",    f"{lives_protected:,}",          delta=f"{lives_protected/population_size*100:.1f}% of population")
    c2.metric("Avg Evacuation Time",f"{reduced_avg_delay:.1f}h",     delta=f"-{time_reduction:.1f}h",  delta_color="inverse")
    c3.metric("In Critical Zone",   f"{reduced_critical_pct*100:.0f}%", delta=f"-{(current_critical_pct-reduced_critical_pct)*100:.0f}%", delta_color="inverse")
    c4.metric("System Efficiency",  f"{adoption_rate}%",             delta="Target: 80%")

    st.markdown("---")
    st.subheader("Evacuation Time Distribution: Current vs. With Caregiver Alerts")

    np.random.seed(42)
    current_delays = np.random.gamma(3, 2.3, population_size)
    reduced_delays = np.maximum(0, current_delays - time_reduction * (adoption_rate / 100))

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=current_delays, name='Current System',                          marker_color='#FF4B4B', opacity=0.6, nbinsx=40))
    fig.add_trace(go.Histogram(x=reduced_delays, name=f'With Caregiver Alerts (-{time_reduction}h)', marker_color='#00CC00', opacity=0.6, nbinsx=40))
    fig.add_vline(x=critical_threshold, line_dash="dash", line_color="black", annotation_text="Critical Threshold (6h)")
    fig.update_layout(barmode='overlay', xaxis_title='Evacuation Delay (hours)', yaxis_title='Number of Individuals', height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Geographic Impact Analysis")
    counties_data = pd.DataFrame({
        'County':            ['Mecklenburg', 'Cabarrus', 'Union', 'Gaston', 'Iredell'],
        'Vulnerable Pop.':   [3420, 1876, 2145, 1598, 1234],
        'Current Avg Delay': [6.9, 7.2, 6.5, 6.8, 7.1],
        'Projected Delay':   [4.9, 5.2, 4.5, 4.8, 5.1],
        'Lives Protected':   [542, 298, 340, 253, 196],
    })
    fig = px.bar(counties_data, x='County', y=['Current Avg Delay', 'Projected Delay'],
                 barmode='group',
                 color_discrete_map={'Current Avg Delay': '#FF4B4B', 'Projected Delay': '#00CC00'},
                 labels={'value': 'Hours', 'variable': 'Scenario'})
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(counties_data, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════
# ABOUT
# ══════════════════════════════════════════════════════════════════════
elif page == "About":
    st.header("About the Caregiver Alert System")
    st.markdown(f"""
    ### The Problem

    Vulnerable populations — including elderly, disabled, and low-income individuals — face **significantly longer
    evacuation delays** during wildfires.  Our analysis reveals:

    - **67% longer** average evacuation times for vulnerable populations
    - **45% of vulnerable individuals** exceed critical evacuation thresholds
    - **Disproportionate impact** on rural and low-income communities

    ### Our Solution

    The **Caregiver Alert System** creates a parallel notification pathway that alerts family members
    and caregivers when wildfires threaten their vulnerable loved ones.

    #### Personalized Risk Assessment
    - Real-time risk scores based on fire proximity + individual vulnerability factors
    - Predictive evacuation windows using machine learning
    - Addresses individual mobility, health, and resource constraints

    #### Proactive Alerts
    - Immediate notifications to pre-registered caregivers
    - Multi-channel delivery (SMS, email, phone)
    - Escalating urgency based on fire progression

    #### Data-Driven Equity Focus
    - Built on comprehensive Social Vulnerability Index (SVI) analysis
    - Prioritises historically underserved communities
    - Continuous monitoring of evacuation disparities

    #### Actionable Guidance
    - Fire perimeter visualisation
    - Optimised evacuation routes (OSRM open-source routing)
    - Categorised shelter locations (women, elderly, disabled, mental health, veterans, pets)
    - Emergency preparation checklists

    ### Technology Stack

    - **Data Analysis:** Python (pandas, scikit-learn, geopandas)
    - **Visualisation:** Streamlit, Plotly, Folium (Leaflet.js)
    - **Routing:** OSRM (open-source, no API key)
    - **Geocoding:** Nominatim / OpenStreetMap
    - **Shelter Discovery:** OpenStreetMap Overpass API
    - **Road Conditions:** NC DOT TIMS REST API (live, no key)
    - **Real-time Fire Data:** NASA FIRMS + NIFC APIs
    - **Vulnerability Data:** CDC Social Vulnerability Index (SVI) 2022

    ### Team: 49ers Intelligence Lab

    WiDS Datathon 2025 participants from UNC Charlotte.

    Currently monitoring **{len(vulnerable_populations)} vulnerable counties**.

    ### Contact
    - Email: layesh1@charlotte.edu
    - GitHub: https://github.com/layesh1/widsdatathon
    - WiDS Conference: April 21–22, 2026
    """)
    st.info("Dashboard page shows real-time fire data.  Analysis pages use WiDS competition dataset.")


# ── footer ───────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray;'>
    <p>49ers Intelligence Lab  ·  WiDS 2025  ·  {len(vulnerable_populations)} counties  ·  {len(fire_data)} fires</p>
</div>
""", unsafe_allow_html=True)