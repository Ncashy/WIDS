"""
evacuation_planner_page.py  —  v5  (Shelter Finder)

This page is now SHELTER-ONLY.  All turn-by-turn directions, transit info,
multimodal route comparison, and the driving/walking/public-transport tabs
have been moved to directions_page.py.

What remains
────────────
• City input → geocode → nearby-fire threat list
• Safe-zone destination picker (dynamic, fire-aware)
• Live shelter discovery (Overpass) + curated static fallback
• Shelter category filter (General | Women/DV | Elderly | Disabled |
  Mental-Health | Veterans | Families | Pet-Friendly | Hospital)
• Shelter-focused map: origin pin, shelter pins colour-coded by category,
  fire circles.  No route polylines — those live on the Directions page.
• Road-condition advisory block (NC DOT TIMS / Caltrans / WSDOT / OSM nationwide)
• Emergency resource footer
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from typing import Dict, List, Optional, Tuple
from math import radians, cos, sin, asin, sqrt
from datetime import datetime


# ── local imports ────────────────────────────────────────────────────
try:
    from us_cities_database import get_city_coordinates
    CITY_DB_AVAILABLE = True
except Exception:
    CITY_DB_AVAILABLE = False

try:
    from transit_and_safezones import get_dynamic_safe_zones
    TRANSIT_DB_AVAILABLE = True
except Exception:
    TRANSIT_DB_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def _haversine(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 3956 * 2 * asin(sqrt(a))


# ══════════════════════════════════════════════════════════════════════
# GEOCODING
# ══════════════════════════════════════════════════════════════════════

def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    if CITY_DB_AVAILABLE:
        coords = get_city_coordinates(address.lower().strip())
        if coords:
            return coords
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1, "countrycodes": "us"},
            headers={"User-Agent": "WiDS-Caregiver-Alert/1.0"},
            timeout=10,
        )
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════
# ROAD-INCIDENT FETCHERS  (nationwide)
# ══════════════════════════════════════════════════════════════════════

NC_COUNTY_IDS: Dict[str, int] = {
    "mecklenburg": 56, "cabarrus": 13, "union": 83, "gaston": 37,
    "iredell": 45, "davidson": 26, "guilford": 41, "wake": 81,
    "forsyth": 38, "durham": 28, "alamance": 1, "johnston": 46,
    "lee": 53, "moore": 65, "chatham": 18, "orange": 68,
    "buncombe": 9, "pitt": 71, "cumberland": 23,
}

CITY_TO_NC_COUNTY = {
    "charlotte": "mecklenburg", "matthews": "mecklenburg",
    "mint hill": "mecklenburg", "huntersville": "mecklenburg",
    "concord": "cabarrus", "kannapolis": "cabarrus",
    "monroe": "union", "indian trail": "union",
    "gastonia": "gaston", "statesville": "iredell",
    "mooresville": "iredell", "davidson": "davidson",
    "greensboro": "guilford", "high point": "guilford",
    "raleigh": "wake", "cary": "wake", "apex": "wake",
    "winston-salem": "forsyth", "kernersville": "forsyth",
    "durham": "durham", "asheville": "buncombe",
}

# ── 50-state + DC DOT / 511 fallback links ──────────────────────────
STATE_DOT_LINKS: Dict[str, Dict[str, str]] = {
    "AL":{"name":"Alabama",         "url":"https://www.aldot.gov/"},
    "AK":{"name":"Alaska",          "url":"https://www.dot.alaska.gov/"},
    "AZ":{"name":"Arizona",         "url":"https://adot.gov/"},
    "AR":{"name":"Arkansas",        "url":"https://www.ardot.gov/"},
    "CA":{"name":"California",      "url":"https://roads.dot.ca.gov/"},
    "CO":{"name":"Colorado",        "url":"https://cotrip.org/"},
    "CT":{"name":"Connecticut",     "url":"https://www.dot.ct.gov/"},
    "DE":{"name":"Delaware",        "url":"https://www.deldot.gov/"},
    "DC":{"name":"D.C.",            "url":"https://ddot.dc.gov/"},
    "FL":{"name":"Florida",         "url":"https://www.fdot.gov/"},
    "GA":{"name":"Georgia",         "url":"https://www.ga511.com/"},
    "HI":{"name":"Hawaii",          "url":"https://www.hawaii.gov/dot/"},
    "ID":{"name":"Idaho",           "url":"https://www.itd.idaho.gov/"},
    "IL":{"name":"Illinois",        "url":"https://www.getaroundillinois.com/"},
    "IN":{"name":"Indiana",         "url":"https://www.in.gov/dot/"},
    "IA":{"name":"Iowa",            "url":"https://www.traveler.iowa.gov/"},
    "KS":{"name":"Kansas",          "url":"https://www.kdot.kansas.gov/"},
    "KY":{"name":"Kentucky",        "url":"https://511.ky.gov/"},
    "LA":{"name":"Louisiana",       "url":"https://www.louisianabelieves.com/"},
    "ME":{"name":"Maine",           "url":"https://www.maine.gov/dot/"},
    "MD":{"name":"Maryland",        "url":"https://www.sha.maryland.gov/"},
    "MA":{"name":"Massachusetts",   "url":"https://www.mass.gov/orgs/massachusetts-department-of-transportation"},
    "MI":{"name":"Michigan",        "url":"https://www.michigan.gov/mdot/"},
    "MN":{"name":"Minnesota",       "url":"https://511.mn.gov/"},
    "MS":{"name":"Mississippi",     "url":"https://www.mdot.ms.gov/"},
    "MO":{"name":"Missouri",        "url":"https://www.modot.mo.gov/"},
    "MT":{"name":"Montana",         "url":"https://www.montana.gov/dot/"},
    "NE":{"name":"Nebraska",        "url":"https://www.nebraska.gov/dot/"},
    "NV":{"name":"Nevada",          "url":"https://www.nevadadot.com/"},
    "NH":{"name":"New Hampshire",   "url":"https://www.nhdot.nh.gov/"},
    "NJ":{"name":"New Jersey",      "url":"https://www.nj511.org/"},
    "NM":{"name":"New Mexico",      "url":"https://www.nmtd.nm.gov/"},
    "NY":{"name":"New York",        "url":"https://www.dot.ny.gov/"},
    "NC":{"name":"North Carolina",  "url":"https://www.ncdot.gov/"},
    "ND":{"name":"North Dakota",    "url":"https://www.dot.nd.gov/"},
    "OH":{"name":"Ohio",            "url":"https://www.ohio511.com/"},
    "OK":{"name":"Oklahoma",        "url":"https://www.odot.ok.gov/"},
    "OR":{"name":"Oregon",          "url":"https://www.oregon511.org/"},
    "PA":{"name":"Pennsylvania",    "url":"https://www.penndot.pa.gov/"},
    "RI":{"name":"Rhode Island",    "url":"https://www.ridot.ri.gov/"},
    "SC":{"name":"South Carolina",  "url":"https://www.scdot.org/"},
    "SD":{"name":"South Dakota",    "url":"https://www.sdtransporation.sd.gov/"},
    "TN":{"name":"Tennessee",       "url":"https://www.tn.gov/tdot/"},
    "TX":{"name":"Texas",           "url":"https://www.txdot.gov/"},
    "UT":{"name":"Utah",            "url":"https://www.udot.utah.gov/"},
    "VT":{"name":"Vermont",         "url":"https://www.vtrans.vermont.gov/"},
    "VA":{"name":"Virginia",        "url":"https://www.vdot.virginia.gov/"},
    "WA":{"name":"Washington",      "url":"https://www.wsdot.wa.gov/"},
    "WV":{"name":"West Virginia",   "url":"https://www.wvdot.com/"},
    "WI":{"name":"Wisconsin",       "url":"https://www.dot.wisconsin.gov/"},
    "WY":{"name":"Wyoming",         "url":"https://www.wyoming.gov/dot/"},
}


def _bbox_str(lat1, lon1, lat2, lon2, pad: float = 0.25) -> str:
    return (f"{min(lat1,lat2)-pad},{min(lon1,lon2)-pad},"
            f"{max(lat1,lat2)+pad},{max(lon1,lon2)+pad}")


@st.cache_data(ttl=120)
def fetch_ncdot_incidents(county_name: str) -> List[Dict]:
    cid = NC_COUNTY_IDS.get(county_name.lower().strip())
    if cid is None:
        return []
    url = f"https://eapps.ncdot.gov/services/traffic-prod/v1/counties/{cid}/incidents"
    try:
        r = requests.get(url, headers={"User-Agent": "WiDS-Caregiver-Alert/1.0"}, timeout=10)
        if r.status_code == 200:
            raw = r.json()
            out = []
            for inc in (raw if isinstance(raw, list) else []):
                out.append({
                    "title":     inc.get("title") or inc.get("Title") or inc.get("description") or "Incident",
                    "road":      inc.get("road") or inc.get("Road") or inc.get("roadway") or "",
                    "severity":  inc.get("severity") or inc.get("Severity") or "",
                    "status":    inc.get("status") or inc.get("Status") or "",
                    "latitude":  inc.get("latitude") or inc.get("Latitude"),
                    "longitude": inc.get("longitude") or inc.get("Longitude"),
                    "source":    "NC DOT TIMS",
                })
            return out
    except Exception:
        pass
    return []


@st.cache_data(ttl=180)
def fetch_caltrans_closures(lat: float, lon: float) -> List[Dict]:
    """Caltrans emergency closures — ArcGIS FeatureServer, no key."""
    url = ("https://gis.dot.ca.gov/arcgis/rest/services/Caltrans/"
           "Caltrans_Emergency_Road_Closures/FeatureServer/0/query")
    params = {
        "where": "1=1",
        "geometry": f"{lon-0.4},{lat-0.4},{lon+0.4},{lat+0.4}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
        "outFields": "COUNTY,ROAD_NAME,CLOSURE_TYPE,DESCRIPTION,LATITUDE,LONGITUDE",
        "returnGeometry": "false", "f": "json",
    }
    try:
        r = requests.get(url, params=params,
                         headers={"User-Agent": "WiDS-Caregiver-Alert/1.0"}, timeout=12)
        if r.status_code != 200:
            return []
        out = []
        for feat in r.json().get("features", []):
            a = feat.get("properties") or feat.get("attributes") or {}
            out.append({
                "title":     a.get("DESCRIPTION") or a.get("CLOSURE_TYPE") or "Road Closure",
                "road":      a.get("ROAD_NAME", ""),
                "severity":  a.get("CLOSURE_TYPE", ""),
                "status":    "Active",
                "latitude":  a.get("LATITUDE"),
                "longitude": a.get("LONGITUDE"),
                "source":    "Caltrans",
            })
        return out
    except Exception:
        return []


@st.cache_data(ttl=120)
def fetch_wsdot_incidents(lat: float, lon: float) -> List[Dict]:
    """WSDOT traveler-info incidents — no key."""
    url = "https://wsdot.wa.gov/trafficapi/rest/Incident/Current"
    try:
        r = requests.get(url,
                         headers={"User-Agent": "WiDS-Caregiver-Alert/1.0"}, timeout=12)
        if r.status_code != 200:
            return []
        raw   = r.json()
        items = raw if isinstance(raw, list) else (raw.get("incidents") or raw.get("Incidents") or [])
        south, north = lat - 0.4, lat + 0.4
        west,  east  = lon - 0.4, lon + 0.4
        out = []
        for inc in items:
            ilat = inc.get("Latitude") or inc.get("latitude")
            ilon = inc.get("Longitude") or inc.get("longitude")
            if ilat is None or ilon is None:
                continue
            if not (south <= ilat <= north and west <= ilon <= east):
                continue
            out.append({
                "title":     inc.get("Description") or inc.get("description") or "Incident",
                "road":      inc.get("LocationDescription") or inc.get("Road") or "",
                "severity":  inc.get("Severity") or inc.get("severity") or "",
                "status":    inc.get("Status") or "Active",
                "latitude":  ilat, "longitude": ilon,
                "source":    "WSDOT",
            })
        return out
    except Exception:
        return []


@st.cache_data(ttl=300)
def fetch_overpass_road_issues(lat: float, lon: float) -> List[Dict]:
    """
    OSM highway nodes/ways tagged construction / road_work / access=no
    in a box around the given point.  Universal fallback — works
    everywhere, no key required.
    """
    bb = _bbox_str(lat, lon, lat, lon, pad=0.3)
    query = (
        f'[out:json][timeout:15];('
        f'  node["highway"]["construction"]{bb};'
        f'  node["highway"]["access"="no"]{bb};'
        f'  way["highway"]["construction"]{bb};'
        f'  way["highway"]["access"="no"]{bb};'
        f'  node["highway"]["road_work"="yes"]{bb};'
        f'  way["highway"]["road_work"="yes"]{bb};'
        f');out center;'
    )
    for ep in OVERPASS_ENDPOINTS:
        try:
            r = requests.post(ep, data={"data": query},
                headers={"User-Agent": "WiDS-Caregiver-Alert/1.0"}, timeout=18)
            if r.status_code != 200:
                continue
            out = []
            for elem in r.json().get("elements", []):
                tags = elem.get("tags", {})
                elat = elem.get("lat") or (elem.get("center") or {}).get("lat")
                elon = elem.get("lon") or (elem.get("center") or {}).get("lon")
                if elat is None or elon is None:
                    continue
                name = tags.get("name", tags.get("highway", "Road"))
                if tags.get("construction"):
                    title = f"Under construction: {tags['construction']}"
                elif tags.get("access") == "no":
                    title = "Access restricted"
                elif tags.get("road_work") == "yes":
                    title = "Road work in progress"
                else:
                    title = "Road issue"
                out.append({
                    "title": title, "road": name,
                    "severity": "Medium", "status": "Active",
                    "latitude": elat, "longitude": elon,
                    "source": "OpenStreetMap",
                })
            return out
        except Exception:
            continue
    return []


def fetch_road_incidents_for_point(state: Optional[str], lat: float, lon: float,
                                   city_name: str) -> List[Dict]:
    """
    Master dispatcher for the shelter page — single-point version.
    Picks the best state-specific source, then always layers on Overpass.
    """
    incidents: List[Dict] = []
    if state == "NC":
        county = CITY_TO_NC_COUNTY.get(city_name.lower().strip())
        if county:
            incidents.extend(fetch_ncdot_incidents(county))
    elif state == "CA":
        incidents.extend(fetch_caltrans_closures(lat, lon))
    elif state == "WA":
        incidents.extend(fetch_wsdot_incidents(lat, lon))
    # Always layer Overpass
    incidents.extend(fetch_overpass_road_issues(lat, lon))
    return incidents


def _extract_state_abbr(address: str) -> Optional[str]:
    US_STATES = {
        "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL",
        "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT",
        "NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI",
        "SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
    }
    for p in reversed(address.replace(",", " ").split()):
        if p.strip().upper() in US_STATES:
            return p.strip().upper()
    return None


# ══════════════════════════════════════════════════════════════════════
# SHELTER DISCOVERY  (Overpass + curated static fallback)
# ══════════════════════════════════════════════════════════════════════

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://api.letsopen.de/api/interpreter",
]

_TAG_CATEGORY_MAP = {
    "dv_shelter":          "Women / Domestic-Violence",
    "elderly_care":        "Elderly",
    "disabled":            "Disabled / ADA",
    "mental_health":       "Mental Health",
    "housing_emergency":   "General Emergency",
    "food_bank":           "Food / Supply Distribution",
    "group_home":          "Group Home",
    "shelter":             "General",
    "social_centre":       "Social Centre",
    "hospital":            "Hospital / Medical",
    "veterinary":          "Pet-Friendly (Veterinary)",
}

SHELTER_CATEGORIES = [
    "General",
    "Women / Domestic-Violence",
    "Elderly",
    "Disabled / ADA",
    "Mental Health",
    "Veterans",
    "Families w/ Children",
    "Pet-Friendly",
    "Hospital / Medical",
]

# Curated static shelters — always present as baseline
STATIC_SHELTER_DB: Dict[str, List[Dict]] = {
    "General": [
        {"name": "Red Cross Shelter (local chapter)",
         "address": "Contact local Red Cross — 1-800-RED-CROSS",
         "lat_offset": 0.0, "lon_offset": 0.0,
         "phone": "1-800-733-2767", "ada": True,
         "note": "Red Cross operates temporary shelters within 24 h of a declared emergency. Call to confirm nearest open location."},
        {"name": "FEMA / County Emergency Shelter",
         "address": "Contact county emergency management or dial 211",
         "lat_offset": 0.0, "lon_offset": 0.0,
         "phone": "211", "ada": True,
         "note": "County-run shelters open automatically when an evacuation order is issued. 211 connects to local emergency services nationwide."},
    ],
    "Women / Domestic-Violence": [
        {"name": "National DV Hotline — Shelter Referral",
         "address": "Referral only — call or text for nearest shelter",
         "lat_offset": 0.0, "lon_offset": 0.0,
         "phone": "1-800-799-7233", "ada": True,
         "note": "The National Domestic Violence Hotline can connect you to the nearest safe, confidential shelter. Text START to 88788."},
    ],
    "Elderly": [
        {"name": "Area Agency on Aging — Emergency Placement",
         "address": "Contact your local AAA for nearest elder shelter",
         "lat_offset": 0.0, "lon_offset": 0.0,
         "phone": "eldercare.acl.gov — 1-800-677-1116", "ada": True,
         "note": "The Eldercare Locator (federal) links to local Area Agencies on Aging who coordinate emergency placement for seniors."},
    ],
    "Disabled / ADA": [
        {"name": "ADA / Disability-Specific Shelter Referral",
         "address": "Contact local emergency management",
         "lat_offset": 0.0, "lon_offset": 0.0,
         "phone": "211", "ada": True,
         "note": "Most county emergency shelters are ADA-compliant. Call 211 and specify mobility / accessibility needs."},
    ],
    "Mental Health": [
        {"name": "988 Suicide & Crisis Lifeline — Shelter Referral",
         "address": "Call or text 988 for crisis support + shelter help",
         "lat_offset": 0.0, "lon_offset": 0.0,
         "phone": "988", "ada": True,
         "note": "988 counsellors can arrange crisis-safe shelter placement and coordinate with local mental-health agencies."},
    ],
    "Veterans": [
        {"name": "VA Emergency / Homeless Veteran Services",
         "address": "Contact nearest VA Medical Center",
         "lat_offset": 0.0, "lon_offset": 0.0,
         "phone": "1-800-273-8255 (Veterans Crisis Line)", "ada": True,
         "note": "The VA operates emergency shelters for veterans through its Homeless Veteran programmes."},
    ],
    "Families w/ Children": [
        {"name": "211 Family-Shelter Referral",
         "address": "Dial 211 and request family shelter",
         "lat_offset": 0.0, "lon_offset": 0.0,
         "phone": "211", "ada": True,
         "note": "Many emergency shelters have dedicated family wings with cots, meals, and childcare. 211 can confirm availability."},
    ],
    "Pet-Friendly": [
        {"name": "ASPCA / Local Animal Rescue — Pet-Friendly Shelter Info",
         "address": "Contact local animal rescue or dial 211",
         "lat_offset": 0.0, "lon_offset": 0.0,
         "phone": "211", "ada": False,
         "note": "Not all emergency shelters accept pets. 211 and local rescues maintain lists of pet-friendly evacuation sites. Bring carriers and records."},
    ],
}


@st.cache_data(ttl=300)
def fetch_overpass_shelters(dest_lat: float, dest_lon: float, radius_m: int = 15000) -> List[Dict]:
    query = f"""
    [out:json][timeout:10];
    (
      node["amenity"="shelter"](around:{radius_m},{dest_lat},{dest_lon});
      node["social_facility"](around:{radius_m},{dest_lat},{dest_lon});
      node["amenity"="hospital"](around:{radius_m},{dest_lat},{dest_lon});
      way["amenity"="shelter"](around:{radius_m},{dest_lat},{dest_lon});
      way["social_facility"](around:{radius_m},{dest_lat},{dest_lon});
    );
    out center;
    """
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            r = requests.post(endpoint, data={"data": query},
                              headers={"User-Agent": "WiDS-Caregiver-Alert/1.0"}, timeout=12)
            if r.status_code != 200:
                continue
            raw = r.json()
            results = []
            for elem in raw.get("elements", []):
                tags = elem.get("tags", {})
                name = tags.get("name", "").strip()
                if not name:
                    continue
                lat = elem.get("lat") or (elem.get("center") or {}).get("lat")
                lon = elem.get("lon") or (elem.get("center") or {}).get("lon")
                if lat is None or lon is None:
                    continue
                sf       = tags.get("social_facility", "")
                amenity  = tags.get("amenity", "")
                category = _TAG_CATEGORY_MAP.get(sf) or _TAG_CATEGORY_MAP.get(amenity) or "General"
                results.append({
                    "name": name, "lat": lat, "lon": lon,
                    "category": category,
                    "phone": tags.get("phone", "").strip() or "N/A",
                    "ada": tags.get("wheelchair", "yes") != "no",
                    "website": tags.get("website", "").strip(),
                    "source": "OpenStreetMap",
                })
            return results
        except Exception:
            continue
    return []


def _merge_shelters(live: List[Dict], dest_lat: float, dest_lon: float) -> Dict[str, List[Dict]]:
    merged: Dict[str, List[Dict]] = {cat: [] for cat in SHELTER_CATEGORIES}
    for s in live:
        cat = s.get("category", "General")
        merged.setdefault(cat, []).append(s)
    for cat, statics in STATIC_SHELTER_DB.items():
        if not merged.get(cat):
            for s in statics:
                merged.setdefault(cat, []).append({
                    "name": s["name"],
                    "lat": dest_lat + s.get("lat_offset", 0),
                    "lon": dest_lon + s.get("lon_offset", 0),
                    "category": cat,
                    "phone": s["phone"], "ada": s["ada"],
                    "note": s["note"], "source": "Curated",
                })
    return merged


# ══════════════════════════════════════════════════════════════════════
# MAIN PAGE RENDERER
# ══════════════════════════════════════════════════════════════════════

def render_evacuation_planner_page(fire_data, vulnerable_populations):
    """Entry point called by the multi-page dashboard."""

    st.title("Find a Shelter")
    st.markdown(
        "Search for emergency shelters near a safe-zone destination — "
        "filtered by population need.  For turn-by-turn directions to any shelter, "
        "use the **Directions & Navigation** page."
    )

    # ── session-state ──
    for key, default in {
        "search_address": None,
        "search_coords": None,
        "search_triggered": False,
        "dynamic_safe_zones": None,
        "selected_zone_idx": 0,
    }.items():
        st.session_state.setdefault(key, default)

    # ── Input ──
    st.subheader("Your Location")
    st.info("500+ US cities, all 50 states.  Type your city — e.g. Charlotte, NC")

    col1, col2 = st.columns([3, 1])
    with col1:
        address = st.text_input(
            "Enter your city",
            value=st.session_state.search_address or "",
            placeholder="Charlotte, NC",
            key="address_input",
        )
    with col2:
        search_button = st.button("Find Shelters", type="primary")

    if search_button and address:
        st.session_state.search_triggered = True
        st.session_state.search_address   = address
        st.session_state.search_coords    = None
        st.session_state.dynamic_safe_zones = None

    # ── Landing ──
    if not st.session_state.search_triggered:
        st.info("Enter your city above to find nearby shelters.")
        st.markdown("---")
        st.subheader("How It Works")
        st.markdown(
            "1. **Enter your city** — geocoded instantly.\n"
            "2. **Nearby fires** — satellite detections within 100 mi.\n"
            "3. **Safe-zone shelters** — specific addresses by population need.\n"
            "4. **Interactive map** — shelter pins colour-coded by category.\n"
            "5. **Directions** — use the Directions & Navigation page for routes to any shelter."
        )
        return

    # ── Geocode ──
    if st.session_state.search_coords is None:
        with st.spinner("Finding your location…"):
            st.session_state.search_coords = geocode_address(st.session_state.search_address)

    coords = st.session_state.search_coords
    if coords is None:
        st.error("City not found. Try 'City, State' format.")
        return

    origin_lat, origin_lon = coords
    st.success(f"Location: **{st.session_state.search_address.strip().title()}**  ({origin_lat:.4f}, {origin_lon:.4f})")

    # ── Safe zones ──
    if st.session_state.dynamic_safe_zones is None:
        with st.spinner("Finding nearby safe zones…"):
            st.session_state.dynamic_safe_zones = get_dynamic_safe_zones(
                origin_lat, origin_lon, fire_data=fire_data,
                min_distance_mi=30, max_distance_mi=600, num_zones=10,
            )
    safe_zone_list: List[Dict] = st.session_state.dynamic_safe_zones or []

    # ── Fire threats ──
    st.subheader("Nearby Fire Threats")
    nearest_fires: List[Dict] = []
    if fire_data is not None and len(fire_data) > 0:
        for _, fire in fire_data.iterrows():
            fl, flo = fire.get("latitude"), fire.get("longitude")
            if fl and flo:
                d = _haversine(origin_lat, origin_lon, fl, flo)
                if d < 100:
                    acres = fire.get("acres", 0)
                    nearest_fires.append({
                        "name": fire.get("fire_name", "Satellite Detection"),
                        "distance": round(d, 1),
                        "acres": acres if (acres and acres == acres) else 0,
                        "lat": fl, "lon": flo,
                    })
    nearest_fires.sort(key=lambda x: x["distance"])

    if nearest_fires:
        st.warning(f"{len(nearest_fires)} fire(s) detected within 100 miles")
        for f in nearest_fires[:5]:
            badge = "HIGH" if f["distance"] < 15 else ("MEDIUM" if f["distance"] < 40 else "LOW")
            acres_str = f"{f['acres']:,.0f} acres" if f["acres"] else "size unknown"
            st.write(f"[{badge}]  {f['name']}  —  {f['distance']} mi away  ({acres_str})")
    else:
        st.success("No fires within 100 miles of your location.")

    # ── Road-condition advisory ──
    st.markdown("---")
    st.subheader("Road-Condition Advisory")
    st.warning(
        "**Always check road conditions before driving.**  "
        "During wildfires, highways may close without notice.  "
        "Call **511** or check your state DOT.  For turn-by-turn with closures, "
        "use the **Directions & Navigation** page."
    )

    state_abbr = _extract_state_abbr(st.session_state.search_address)
    city_name  = st.session_state.search_address.lower().strip().split(",")[0].strip()

    with st.spinner("Checking road conditions…"):
        incidents = fetch_road_incidents_for_point(
            state_abbr, coords[0], coords[1], city_name)

    if incidents:
        # Group by source for clear labelling
        by_source: Dict[str, List[Dict]] = {}
        for inc in incidents:
            by_source.setdefault(inc.get("source", "Other"), []).append(inc)

        st.warning(
            f"**{len(incidents)} road issue(s) near {city_name.title()}**  "
            f"*(updated {datetime.now().strftime('%H:%M')})*"
        )
        for source, group in by_source.items():
            st.markdown(f"**{source}** — {len(group)} issue(s)")
            for inc in group[:6]:
                title    = inc.get("title", "Incident")
                road     = inc.get("road", "")
                severity = inc.get("severity", "")
                status   = inc.get("status", "")
                line     = f"- **{title}**"
                if road:     line += f" — {road}"
                if severity: line += f"  `{severity}`"
                if status:   line += f" `{status}`"
                st.markdown(line)
            if len(group) > 6:
                st.caption(f"  … and {len(group)-6} more.")
    else:
        st.success("No road issues detected near your area right now.")

    # Always show correct state DOT link
    if state_abbr and state_abbr in STATE_DOT_LINKS:
        dot = STATE_DOT_LINKS[state_abbr]
        st.caption(
            f"Full {dot['name']} conditions: "
            f"[{dot['name']} DOT]({dot['url']})  •  Call **511** anywhere in the US."
        )
    else:
        st.caption("Call **511** from anywhere in the US for real-time road conditions.")

    # ── Destination picker ──
    st.markdown("---")
    st.subheader("Evacuation Destination")

    if not safe_zone_list:
        st.warning("No safe zones found. Try a different starting city.")
        return

    zone_labels = []
    for z in safe_zone_list:
        tags = ""
        if z["has_rail"]:  tags += " [rail]"
        if z["near_fire"]: tags += " [fire nearby]"
        zone_labels.append(f"{z['name']}  —  {z['distance_mi']} mi{tags}")

    sel_idx = st.selectbox(
        "Select safe-zone city",
        options=range(len(zone_labels)),
        format_func=lambda i: zone_labels[i],
        index=min(st.session_state.selected_zone_idx, len(zone_labels) - 1),
        help="[rail] = rail available  ·  [fire nearby] = fire detected — prefer other options",
        key="safe_zone_select",
    )
    st.session_state.selected_zone_idx = sel_idx
    zone = safe_zone_list[sel_idx]
    dest_lat, dest_lon = zone["lat"], zone["lon"]
    dest_name = zone["name"]

    # ── SHELTER CARDS ──
    st.markdown("---")
    st.subheader("Shelters at Destination")

    with st.spinner("Searching for shelters…"):
        live_shelters = fetch_overpass_shelters(dest_lat, dest_lon)
    all_shelters_by_cat = _merge_shelters(live_shelters, dest_lat, dest_lon)

    available_cats = [c for c in SHELTER_CATEGORIES if all_shelters_by_cat.get(c)]
    chosen_cats = st.multiselect(
        "Filter by shelter type",
        options=available_cats,
        default=available_cats,
    )

    for cat in chosen_cats or available_cats:
        shelters = all_shelters_by_cat.get(cat, [])
        if not shelters:
            continue
        st.markdown(f"#### {cat}")
        for s in shelters:
            with st.expander(s["name"], expanded=(cat == "General")):
                if s.get("note"):
                    st.info(s["note"])
                if s.get("address"):
                    st.markdown(f"Address: {s['address']}")
                cols = st.columns(3)
                cols[0].markdown(f"Phone: **{s.get('phone','N/A')}**")
                cols[1].markdown(f"ADA: **{'Yes' if s.get('ada') else 'No'}**")
                cols[2].markdown(f"Source: *{s.get('source','—')}*")
                if s.get("website"):
                    st.markdown(f"[Website]({s['website']})")

    # ── CTA to Directions page ──
    st.markdown("---")
    st.info(
        "Ready to get directions to one of these shelters?  "
        "Switch to the **Directions & Navigation** page and enter the shelter "
        "address as your destination — it supports driving, walking, transit, and combined routes."
    )

    # ── SHELTER MAP  (no route polylines — those are on Directions page) ──
    st.markdown("---")
    st.subheader("Shelter Map")

    mid_lat  = (origin_lat + dest_lat) / 2
    mid_lon  = (origin_lon + dest_lon) / 2
    dist_mi  = _haversine(origin_lat, origin_lon, dest_lat, dest_lon)
    zoom     = 8 if dist_mi > 80 else (10 if dist_mi > 30 else 12)

    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=zoom, tiles="CartoDB positron")

    # Origin pin
    folium.Marker(
        [origin_lat, origin_lon],
        popup=f"<b>YOUR LOCATION</b><br>{st.session_state.search_address.strip().title()}",
        icon=folium.Icon(color="green", icon="home", prefix="fa"),
        tooltip="Your Location",
    ).add_to(m)

    # Destination pin
    folium.Marker(
        [dest_lat, dest_lon],
        popup=f"<b>SAFE ZONE</b><br>{dest_name}",
        icon=folium.Icon(color="blue", icon="map-marker", prefix="fa"),
        tooltip=f"Safe Zone: {dest_name}",
    ).add_to(m)

    # Shelter pins
    cat_colours = {
        "General": "blue", "Women / Domestic-Violence": "purple",
        "Elderly": "orange", "Disabled / ADA": "cadetblue",
        "Mental Health": "darkblue", "Veterans": "darkgreen",
        "Families w/ Children": "pink", "Pet-Friendly": "beige",
        "Hospital / Medical": "red",
    }
    for cat in SHELTER_CATEGORIES:
        for s in all_shelters_by_cat.get(cat, []):
            if not s.get("lat") or not s.get("lon"):
                continue
            colour = cat_colours.get(cat, "gray")
            folium.Marker(
                [s["lat"], s["lon"]],
                popup=(
                    f"<b>{s['name']}</b><br>"
                    f"<i>{cat}</i><br>"
                    f"Phone: {s.get('phone','—')}<br>"
                    f"{'ADA accessible' if s.get('ada') else ''}"
                ),
                icon=folium.Icon(color=colour, icon="flag", prefix="fa"),
                tooltip=f"{s['name']} ({cat})",
            ).add_to(m)

    # Fire circles
    for f in nearest_fires[:10]:
        folium.Circle(
            [f["lat"], f["lon"]],
            radius=max(f.get("acres", 100) * 40, 800),
            color="red", fill=True, fillColor="orange", fillOpacity=0.35,
            popup=f"{f['name']}  —  {f['distance']} mi away",
        ).add_to(m)

    # Legend
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
         background:white;padding:12px 16px;border-radius:8px;
         border:2px solid #ccc;font-size:13px;box-shadow:0 2px 6px rgba(0,0,0,.3);">
     <b>Legend</b><br>
     <span style="color:green;">&#9679;</span> You &nbsp;
     <span style="color:blue;">&#9679;</span> Safe Zone &nbsp;
     <span style="color:red;">&#9679;</span> Fire<br>
     <span style="color:blue;">&#9632;</span> General &nbsp;
     <span style="color:purple;">&#9632;</span> Women/DV &nbsp;
     <span style="color:orange;">&#9632;</span> Elderly &nbsp;
     <span style="color:darkgreen;">&#9632;</span> Veterans &nbsp;
     <span style="color:red;">&#9632;</span> Hospital
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(m, width="100%", height=600, key="evac_shelter_map")

    # ── Emergency resources ──
    st.markdown("---")
    st.subheader("Emergency Resources")
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        "**Emergency Lines**\n"
        "- 911 — Fire / Police / Medical\n"
        "- 211 — Evacuation assistance\n"
        "- 988 — Suicide & Crisis Lifeline\n"
        "- 1-800-RED-CROSS — Shelter referral\n"
        "- Local AM/FM emergency broadcast"
    )
    c2.markdown(
        "**Evacuation Checklist**\n"
        "- IDs, insurance docs\n"
        "- Medications (7-day supply)\n"
        "- Pet food + carriers\n"
        "- Cash + cards\n"
        "- Phone charger / power bank"
    )
    c3.markdown(
        "**Road Safety**\n"
        "- Call 511 for road conditions\n"
        "- Fill gas tank NOW\n"
        "- Water + snacks for 24 h\n"
        "- Download offline maps"
    )


# ── standalone test ──────────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(page_title="Find a Shelter", layout="wide")
    render_evacuation_planner_page(None, None)
