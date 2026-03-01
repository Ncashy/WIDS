"""
directions_page.py  —  v1

Standalone "Directions & Navigation" page for the WiDS Caregiver Alert app.

What this page does
───────────────────
Google-Maps-style point-A-to-point-B directions with four transport modes:

  1. Driving        – OSRM car profile  (turn-by-turn + polyline)
  2. Walking        – OSRM foot profile (turn-by-turn + polyline)
  3. Public Transit – heuristic stop-finder via Overpass + walk-ride-walk
                      itinerary with real transit-stop pins on map
  4. Combined       – drive-to-nearest-transit-hub, then ride, then short walk

Integrated layers on the interactive map
─────────────────────────────────────────
  • Route polylines colour-coded per mode (active = bold, others = faint)
  • Fire-danger circles (from live MODIS/VIIRS data passed in by the dashboard)
  • Road-closure advisory pins (NC DOT TIMS / Caltrans / WSDOT / OSM nationwide)
  • Transit-stop pins pulled live from OpenStreetMap Overpass
  • OSM road-layer overlay for visual traffic context

Free / open APIs used  (no paid key required for core routing)
───────────────────────────────────────────────────────────────
  • Nominatim        – geocoding          (OSM, no key)
  • OSRM            – car / foot routing  (project-osrm.org, no key)
  • Overpass        – transit stops       (overpass-api.de, no key)
  • NC DOT TIMS     – road incidents (NC)   (eapps.ncdot.gov, no key)
  • Caltrans        – emergency closures (CA) (gis.dot.ca.gov ArcGIS, no key)
  • WSDOT           – traveler incidents (WA) (wsdot.wa.gov, no key)
  • Overpass        – construction/closure tags (all states fallback, no key)
  • Leaflet / OSM   – base map + road overlay (no key)
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
    from transit_and_safezones import get_transit_info
    TRANSIT_DB_AVAILABLE = True
except Exception:
    TRANSIT_DB_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════

OSRM_BASE = "http://router.project-osrm.org/route/v1"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://api.letsopen.de/api/interpreter",
]

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

# ── Major intercity-bus terminals (Greyhound / FlixBus / Megabus) ────
# Static seed so the page always has intercity options even if Overpass
# returns nothing.  Each entry: (city_display, lat, lon, carriers, address)
INTERCITY_TERMINALS: List[Dict] = [
    # Southeast
    {"city":"Charlotte, NC",        "lat":35.2272, "lon":-80.8431, "carriers":["Greyhound","FlixBus"],        "address":"601 E Trade St"},
    {"city":"Raleigh, NC",          "lat":35.7721, "lon":-78.6386, "carriers":["Greyhound","FlixBus"],        "address":"316 W Jones St"},
    {"city":"Atlanta, GA",          "lat":33.7490, "lon":-84.3880, "carriers":["Greyhound","FlixBus"],        "address":"227 Peachtree St NE"},
    {"city":"Miami, FL",            "lat":25.7617, "lon":-80.1918, "carriers":["Greyhound","FlixBus"],        "address":"3801 NW 7th St"},
    {"city":"Orlando, FL",          "lat":28.5383, "lon":-81.3792, "carriers":["Greyhound","FlixBus"],        "address":"1717 S Orange Blossom Trail"},
    {"city":"Nashville, TN",        "lat":36.1627, "lon":-86.7816, "carriers":["Greyhound","FlixBus"],        "address":"200 S 11th Ave"},
    {"city":"New Orleans, LA",      "lat":29.9511, "lon":-90.0715, "carriers":["Greyhound","FlixBus"],        "address":"1522 Tulane Ave"},
    {"city":"Birmingham, AL",       "lat":33.5206, "lon":-86.8024, "carriers":["Greyhound"],                  "address":"2100 11th Ave N"},
    # Northeast
    {"city":"New York, NY",         "lat":40.7580, "lon":-73.9855, "carriers":["Greyhound","FlixBus","Megabus"], "address":"Port Authority Bus Terminal, 42nd St"},
    {"city":"Washington, DC",       "lat":38.8951, "lon":-77.0369, "carriers":["Greyhound","FlixBus","Megabus"], "address":"1200 1st Ave NE"},
    {"city":"Philadelphia, PA",     "lat":39.9526, "lon":-75.1652, "carriers":["Greyhound","FlixBus","Megabus"], "address":"1100 Market St"},
    {"city":"Boston, MA",           "lat":42.3601, "lon":-71.0589, "carriers":["Greyhound","FlixBus","Megabus"], "address":"South Station"},
    {"city":"Baltimore, MD",        "lat":39.2904, "lon":-76.6122, "carriers":["Greyhound","FlixBus"],        "address":"2400 W Baltimore St"},
    {"city":"Pittsburgh, PA",       "lat":40.4406, "lon":-79.9959, "carriers":["Greyhound","FlixBus"],        "address":"2702 Liberty Ave"},
    # Midwest
    {"city":"Chicago, IL",          "lat":41.8781, "lon":-87.6298, "carriers":["Greyhound","FlixBus","Megabus"], "address":"141 W Jackson Blvd"},
    {"city":"Detroit, MI",          "lat":42.3314, "lon":-83.0458, "carriers":["Greyhound","FlixBus"],        "address":"1200 Howard St"},
    {"city":"Cleveland, OH",        "lat":41.4993, "lon":-81.6944, "carriers":["Greyhound","FlixBus"],        "address":"2828 Ontario St"},
    {"city":"Indianapolis, IN",     "lat":39.7684, "lon":-86.1581, "carriers":["Greyhound","FlixBus"],        "address":"350 E Washington St"},
    {"city":"Minneapolis, MN",      "lat":44.9778, "lon":-93.2650, "carriers":["Greyhound","FlixBus"],        "address":"24 E Hennepin Ave"},
    {"city":"St. Louis, MO",        "lat":38.6270, "lon":-90.1994, "carriers":["Greyhound","FlixBus"],        "address":"892 St. Ferdinand St"},
    {"city":"Milwaukee, WI",        "lat":43.0389, "lon":-87.9065, "carriers":["Greyhound","FlixBus"],        "address":"105 N 6th St"},
    # South / Southwest
    {"city":"Dallas, TX",           "lat":32.7767, "lon":-96.7970, "carriers":["Greyhound","FlixBus"],        "address":"8525 Stemmons Fwy"},
    {"city":"Houston, TX",          "lat":29.7604, "lon":-95.3698, "carriers":["Greyhound","FlixBus"],        "address":"2041 Polk St"},
    {"city":"San Antonio, TX",      "lat":29.4241, "lon":-98.4936, "carriers":["Greyhound","FlixBus"],        "address":"127 Concepcion St"},
    {"city":"Austin, TX",           "lat":30.2672, "lon":-97.7431, "carriers":["Greyhound","FlixBus"],        "address":"916 W 6th St"},
    {"city":"Phoenix, AZ",          "lat":33.4484, "lon":-112.0740,"carriers":["Greyhound","FlixBus"],        "address":"2121 W Indian School Rd"},
    {"city":"Albuquerque, NM",      "lat":35.0844, "lon":-106.6504,"carriers":["Greyhound"],                  "address":"201 E Tijeras Ave"},
    {"city":"Oklahoma City, OK",    "lat":35.4676, "lon":-97.5164, "carriers":["Greyhound","FlixBus"],        "address":"712 SW 8th St"},
    # West
    {"city":"Los Angeles, CA",      "lat":34.0522, "lon":-118.2437,"carriers":["Greyhound","FlixBus","Megabus"], "address":"1716 E 7th St"},
    {"city":"San Francisco, CA",    "lat":37.7749, "lon":-122.4194,"carriers":["Greyhound","FlixBus","Megabus"], "address":"200 Folsom St"},
    {"city":"San Diego, CA",        "lat":32.7157, "lon":-117.1611,"carriers":["Greyhound","FlixBus"],        "address":"120 W Broadway"},
    {"city":"Sacramento, CA",       "lat":38.5816, "lon":-121.4944,"carriers":["Greyhound","FlixBus"],        "address":"801 L St"},
    {"city":"Seattle, WA",          "lat":47.6062, "lon":-122.3321,"carriers":["Greyhound","FlixBus"],        "address":"611 2nd Ave"},
    {"city":"Portland, OR",         "lat":45.5152, "lon":-122.6784,"carriers":["Greyhound","FlixBus"],        "address":"550 NW Broadway"},
    {"city":"Denver, CO",           "lat":39.7392, "lon":-104.9903,"carriers":["Greyhound","FlixBus"],        "address":"1700 E Colfax Ave"},
    {"city":"Salt Lake City, UT",   "lat":40.7608, "lon":-111.8910,"carriers":["Greyhound","FlixBus"],        "address":"300 S 400 W"},
    {"city":"Las Vegas, NV",        "lat":36.1699, "lon":-115.1398,"carriers":["Greyhound","FlixBus"],        "address":"5100 S Decatur Blvd"},
    {"city":"Boise, ID",            "lat":43.6150, "lon":-116.2023,"carriers":["Greyhound"],                  "address":"501 S Main St"},
    # Hawaii / Alaska (limited)
    {"city":"Honolulu, HI",         "lat":21.3069, "lon":-157.8583,"carriers":["TheHawaiiBus"],               "address":"Ala Moana Center"},
    {"city":"Anchorage, AK",        "lat":61.2181, "lon":-149.9003,"carriers":["Greyhound"],                  "address":"321 E 5th Ave"},
]


def _nearest_intercity_terminals(lat, lon, terminals: List[Dict], n: int = 5) -> List[Dict]:
    """Return the n closest intercity terminals to (lat, lon), with distance added."""
    out = []
    for t in terminals:
        d = _haversine(lat, lon, t["lat"], t["lon"])
        out.append({**t, "dist_mi": round(d, 1)})
    return sorted(out, key=lambda x: x["dist_mi"])[:n]
MODE_COLOURS = {
    "car":       "#2563eb",   # blue
    "foot":      "#16a34a",   # green
    "walk":      "#16a34a",   # green
    "walk_to":   "#16a34a",   # green
    "walk_from": "#16a34a",   # green
    "ride":      "#9333ea",   # purple
    "drive":     "#2563eb",   # blue
    "coach":     "#0d9488",   # teal
}

MODE_DASH = {
    "car":       None,
    "foot":      "8 4",
    "walk":      "8 4",
    "walk_to":   "8 4",
    "walk_from": "8 4",
    "ride":      None,
    "drive":     None,
    "coach":     "12 6",
}


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def _fmt(minutes: float) -> str:
    minutes = int(round(minutes))
    h, m = divmod(minutes, 60)
    return f"{h} hr {m} min" if h else f"{m} min"


def _haversine(lat1, lon1, lat2, lon2) -> float:
    """Miles between two lat/lon points."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 3956 * 2 * asin(sqrt(a))


def _extract_state(address: str) -> Optional[str]:
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
# GEOCODING
# ══════════════════════════════════════════════════════════════════════

def geocode(address: str) -> Optional[Tuple[float, float]]:
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
# OSRM ROUTING  (car | foot | bicycle — no key)
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def osrm_route(olat, olon, dlat, dlon, profile: str = "car") -> Optional[Dict]:
    """
    Returns dict: distance_mi, duration_min, geometry [[lon,lat],...], steps [str,...]
    """
    url = f"{OSRM_BASE}/{profile}/{olon},{olat};{dlon},{dlat}"
    try:
        r = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson", "steps": "true"},
            timeout=20,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("code") != "Ok":
            return None
        route = data["routes"][0]
        steps = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                instr = step.get("maneuver", {}).get("instruction", "")
                dist_mi = step.get("distance", 0) * 0.000621371
                dur_s   = step.get("duration", 0)
                name    = step.get("name", "")
                if instr:
                    label = instr
                    if name:
                        label += f" on {name}"
                    label += f"  ({dist_mi:.2f} mi"
                    if dur_s:
                        label += f", {int(round(dur_s / 60))} min"
                    label += ")"
                    steps.append(label)
        return {
            "distance_mi": round(route["distance"] * 0.000621371, 1),
            "duration_min": round(route["duration"] / 60, 1),
            "geometry": route["geometry"]["coordinates"],
            "steps": steps,
        }
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════
# TRANSIT-STOP DISCOVERY  (Overpass — no key)
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=600)
def fetch_transit_stops(lat: float, lon: float, radius_m: int = 8000) -> List[Dict]:
    """
    Pull bus / rail / tram stops near a point.
    Returns [{name, lat, lon, type, ref, operator}, …]
    """
    query = f"""
    [out:json][timeout:12];
    (
      node["highway"="bus_stop"](around:{radius_m},{lat},{lon});
      node["railway"~"station|halt|tram_stop"](around:{radius_m},{lat},{lon});
      node["amenity"="bus_station"](around:{radius_m},{lat},{lon});
      node["public_transport"~"stop|station|platform"](around:{radius_m},{lat},{lon});
      node["amenity"="bus_station"]["operator"~"[Gg]reyhound|[Ff]lix[Bb]us|[Mm]ega[Bb]us"](around:{radius_m},{lat},{lon});
      node["route"~"bus|coach"](around:{radius_m},{lat},{lon});
      way["amenity"="bus_station"](around:{radius_m},{lat},{lon});
      way["public_transport"="station"](around:{radius_m},{lat},{lon});
    );
    out center;
    """
    for ep in OVERPASS_ENDPOINTS:
        try:
            r = requests.post(
                ep,
                data={"data": query},
                headers={"User-Agent": "WiDS-Caregiver-Alert/1.0"},
                timeout=15,
            )
            if r.status_code != 200:
                continue
            raw = r.json()
            for elem in raw.get("elements", []):
                tags = elem.get("tags", {})
                name = tags.get("name", "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                slat = elem.get("lat") or (elem.get("center") or {}).get("lat")
                slon = elem.get("lon") or (elem.get("center") or {}).get("lon")
                if slat is None or slon is None:
                    continue
                # Detect intercity coach first (most specific)
                op = (tags.get("operator") or "").lower()
                is_intercity = any(k in op for k in ("greyhound", "flixbus", "megabus", "coach"))
                if is_intercity or tags.get("route") == "coach":
                    stype = "Intercity Coach"
                elif tags.get("railway") in ("station", "halt"):
                    stype = "Rail"
                elif tags.get("railway") == "tram_stop":
                    stype = "Tram"
                elif tags.get("amenity") == "bus_station":
                    stype = "Bus Station"
                elif tags.get("public_transport") == "platform":
                    stype = "Platform"
                else:
                    stype = "Bus"
                stops.append({
                    "name": name, "lat": slat, "lon": slon,
                    "type": stype,
                    "ref": tags.get("ref", ""),
                    "operator": tags.get("operator", ""),
                })
            return stops
        except Exception:
            continue
    return []


def _nearest_stop(lat, lon, stops: List[Dict]) -> Optional[Dict]:
    best, best_d = None, 99999
    for s in stops:
        d = _haversine(lat, lon, s["lat"], s["lon"])
        if d < best_d:
            best_d, best = d, {**s, "distance_mi": round(d, 2)}
    return best


# ══════════════════════════════════════════════════════════════════════
# MULTIMODAL ROUTE OPTIONS  (Google Maps-style: multiple ranked plans)
# ══════════════════════════════════════════════════════════════════════
# Each "plan" is a list of legs.  Each leg: {mode, label, duration_min,
# dist_mi, geometry, stop_name}.  Plans are ranked and labelled
# (Fastest, Fewest Transfers, Most Walking, etc.).

_WALK_SPEED_MPH = 3.2
_BUS_SPEED_MPH  = 22.0
_RAIL_SPEED_MPH = 40.0
_CAR_SPEED_MPH  = 35.0   # urban average
_BOARD_BUF_MIN  = 5      # boarding buffer per transfer

def _leg(mode: str, label: str, dur: float, dist: float, geom: list, stop: str = "") -> Dict:
    return {"mode": mode, "label": label, "duration_min": round(dur, 1),
            "dist_mi": round(dist, 2), "geometry": geom, "stop": stop}


def _dur_from_route(r, fallback_dist_mi, speed_mph):
    if r and r.get("duration_min"):
        return r["duration_min"]
    return round(fallback_dist_mi / speed_mph * 60, 1)


def build_multimodal_options(olat, olon, dlat, dlon,
                             origin_stops, dest_stops,
                             nearby_intercity) -> List[Dict]:
    """
    Returns a list of plan dicts, each with:
        label   – e.g. "Fastest", "Fewest Transfers"
        tag     – short badge text
        legs    – ordered list of leg dicts
        total_min
        total_dist_mi
        transfers – number of mode-switches
    """
    plans: List[Dict] = []
    o_all = origin_stops or []
    d_all = dest_stops   or []
    straight = _haversine(olat, olon, dlat, dlon)

    # helpers to find stops by type
    def _by_type(stops, *types):
        return [s for s in stops if s["type"] in types]

    def _near(lat, lon, stops):
        return _nearest_stop(lat, lon, stops) if stops else None

    # ── PLAN A: Pure walk ──────────────────────────────────────────
    walk_r = osrm_route(olat, olon, dlat, dlon, "foot")
    walk_dur = _dur_from_route(walk_r, straight * 1.2, _WALK_SPEED_MPH)
    plans.append({
        "label": "Walk",
        "tag":   "All walking",
        "legs":  [_leg("walk", "Walk to destination", walk_dur, straight * 1.2,
                       walk_r["geometry"] if walk_r else [], "")],
        "total_min": walk_dur,
        "total_dist_mi": round(straight * 1.2, 1),
        "transfers": 0,
    })

    # ── PLAN B: Pure drive ─────────────────────────────────────────
    car_r = osrm_route(olat, olon, dlat, dlon, "car")
    car_dur  = _dur_from_route(car_r, straight * 1.3, _CAR_SPEED_MPH)
    car_dist = car_r["distance_mi"] if car_r else round(straight * 1.3, 1)
    plans.append({
        "label": "Drive",
        "tag":   "All driving",
        "legs":  [_leg("car", "Drive to destination", car_dur, car_dist,
                       car_r["geometry"] if car_r else [], "")],
        "total_min": car_dur,
        "total_dist_mi": round(car_dist, 1),
        "transfers": 0,
    })

    # ── helper: build a walk→ride→walk plan given an origin & dest stop ──
    def _walk_ride_walk(o_stop, d_stop, ride_speed, ride_label_prefix) -> Optional[Dict]:
        if not o_stop or not d_stop:
            return None
        w1_r  = osrm_route(olat, olon, o_stop["lat"], o_stop["lon"], "foot")
        ride_r = osrm_route(o_stop["lat"], o_stop["lon"], d_stop["lat"], d_stop["lon"], "car")
        w2_r  = osrm_route(d_stop["lat"], d_stop["lon"], dlat, dlon, "foot")

        d_w1   = _haversine(olat, olon, o_stop["lat"], o_stop["lon"])
        d_ride = _haversine(o_stop["lat"], o_stop["lon"], d_stop["lat"], d_stop["lon"])
        d_w2   = _haversine(d_stop["lat"], d_stop["lon"], dlat, dlon)

        t_w1   = _dur_from_route(w1_r, d_w1, _WALK_SPEED_MPH)
        t_ride = round(d_ride / ride_speed * 60, 1)
        t_w2   = _dur_from_route(w2_r, d_w2, _WALK_SPEED_MPH)
        total  = round(t_w1 + _BOARD_BUF_MIN + t_ride + t_w2, 1)

        legs = []
        if t_w1 > 0.5:
            legs.append(_leg("walk", f"Walk to {o_stop['name']}", t_w1, d_w1,
                             w1_r["geometry"] if w1_r else [], o_stop["name"]))
        legs.append(_leg("ride", f"{ride_label_prefix} {o_stop['name']} → {d_stop['name']}",
                         t_ride + _BOARD_BUF_MIN, d_ride,
                         ride_r["geometry"] if ride_r else [], o_stop["name"]))
        if t_w2 > 0.5:
            legs.append(_leg("walk", f"Walk from {d_stop['name']}", t_w2, d_w2,
                             w2_r["geometry"] if w2_r else [], d_stop["name"]))
        return {"legs": legs, "total_min": total,
                "total_dist_mi": round(d_w1 + d_ride + d_w2, 1), "transfers": len(legs) - 1}

    # ── helper: drive → ride → walk ─────────────────────────────────
    def _drive_ride_walk(hub, d_stop, ride_speed, ride_label_prefix) -> Optional[Dict]:
        if not hub or not d_stop:
            return None
        drv_r  = osrm_route(olat, olon, hub["lat"], hub["lon"], "car")
        ride_r = osrm_route(hub["lat"], hub["lon"], d_stop["lat"], d_stop["lon"], "car")
        w_r    = osrm_route(d_stop["lat"], d_stop["lon"], dlat, dlon, "foot")

        d_drv  = _haversine(olat, olon, hub["lat"], hub["lon"])
        d_ride = _haversine(hub["lat"], hub["lon"], d_stop["lat"], d_stop["lon"])
        d_w    = _haversine(d_stop["lat"], d_stop["lon"], dlat, dlon)

        t_drv  = _dur_from_route(drv_r, d_drv, _CAR_SPEED_MPH)
        t_ride = round(d_ride / ride_speed * 60, 1)
        t_w    = _dur_from_route(w_r, d_w, _WALK_SPEED_MPH)
        total  = round(t_drv + _BOARD_BUF_MIN + t_ride + t_w, 1)

        legs = [
            _leg("car",  f"Drive to {hub['name']}", t_drv, d_drv,
                 drv_r["geometry"] if drv_r else [], hub["name"]),
            _leg("ride", f"{ride_label_prefix} {hub['name']} → {d_stop['name']}",
                 t_ride + _BOARD_BUF_MIN, d_ride,
                 ride_r["geometry"] if ride_r else [], hub["name"]),
        ]
        if t_w > 0.5:
            legs.append(_leg("walk", f"Walk from {d_stop['name']}", t_w, d_w,
                             w_r["geometry"] if w_r else [], d_stop["name"]))
        return {"legs": legs, "total_min": total,
                "total_dist_mi": round(d_drv + d_ride + d_w, 1), "transfers": len(legs) - 1}

    # ── PLAN C: Walk → Rail → Walk  (if rail stops exist) ──────────
    o_rail = _near(olat, olon, _by_type(o_all, "Rail"))
    d_rail = _near(dlat, dlon, _by_type(d_all, "Rail"))
    wrw_rail = _walk_ride_walk(o_rail, d_rail, _RAIL_SPEED_MPH, "Rail")
    if wrw_rail:
        plans.append({**wrw_rail, "label": "Rail",  "tag": "Walk · Rail · Walk"})

    # ── PLAN D: Walk → Bus → Walk ──────────────────────────────────
    o_bus = _near(olat, olon, _by_type(o_all, "Bus", "Bus Station"))
    d_bus = _near(dlat, dlon, _by_type(d_all, "Bus", "Bus Station"))
    wrw_bus = _walk_ride_walk(o_bus, d_bus, _BUS_SPEED_MPH, "Bus")
    if wrw_bus:
        plans.append({**wrw_bus, "label": "Bus",    "tag": "Walk · Bus · Walk"})

    # ── PLAN E: Drive → Rail → Walk ────────────────────────────────
    drw_rail = _drive_ride_walk(o_rail, d_rail, _RAIL_SPEED_MPH, "Rail")
    if drw_rail:
        plans.append({**drw_rail, "label": "Drive + Rail", "tag": "Drive · Rail · Walk"})

    # ── PLAN F: Drive → Bus → Walk ─────────────────────────────────
    drw_bus = _drive_ride_walk(o_bus, d_bus, _BUS_SPEED_MPH, "Bus")
    if drw_bus:
        plans.append({**drw_bus, "label": "Drive + Bus", "tag": "Drive · Bus · Walk"})

    # ── PLAN G: Walk → Rail → Walk → Bus → Walk  (rail + bus transfer) ──
    # Only if we have rail at origin and bus at destination (or vice-versa)
    if o_rail and d_bus:
        # find a bus stop near the rail dest stop as a transfer point
        mid_bus = _near(d_rail["lat"], d_rail["lon"], _by_type(d_all, "Bus", "Bus Station")) if d_rail else None
        if mid_bus and d_bus:
            w1_r  = osrm_route(olat, olon, o_rail["lat"], o_rail["lon"], "foot")
            r1_r  = osrm_route(o_rail["lat"], o_rail["lon"], d_rail["lat"], d_rail["lon"], "car") if d_rail else None
            w2_r  = osrm_route(d_rail["lat"], d_rail["lon"], mid_bus["lat"], mid_bus["lon"], "foot") if d_rail else None
            r2_r  = osrm_route(mid_bus["lat"], mid_bus["lon"], d_bus["lat"], d_bus["lon"], "car")
            w3_r  = osrm_route(d_bus["lat"], d_bus["lon"], dlat, dlon, "foot")

            d1 = _haversine(olat, olon, o_rail["lat"], o_rail["lon"])
            d2 = _haversine(o_rail["lat"], o_rail["lon"], d_rail["lat"], d_rail["lon"]) if d_rail else 0
            d3 = _haversine(d_rail["lat"], d_rail["lon"], mid_bus["lat"], mid_bus["lon"]) if d_rail else 0
            d4 = _haversine(mid_bus["lat"], mid_bus["lon"], d_bus["lat"], d_bus["lon"])
            d5 = _haversine(d_bus["lat"], d_bus["lon"], dlat, dlon)

            t1 = _dur_from_route(w1_r, d1, _WALK_SPEED_MPH)
            t2 = round(d2 / _RAIL_SPEED_MPH * 60, 1)
            t3 = _dur_from_route(w2_r, d3, _WALK_SPEED_MPH)
            t4 = round(d4 / _BUS_SPEED_MPH * 60, 1)
            t5 = _dur_from_route(w3_r, d5, _WALK_SPEED_MPH)
            total = round(t1 + _BOARD_BUF_MIN + t2 + t3 + _BOARD_BUF_MIN + t4 + t5, 1)

            legs = []
            if t1 > 0.5:
                legs.append(_leg("walk", f"Walk to {o_rail['name']}", t1, d1, w1_r["geometry"] if w1_r else []))
            legs.append(_leg("ride", f"Rail {o_rail['name']} → {d_rail['name'] if d_rail else '…'}", t2 + _BOARD_BUF_MIN, d2, r1_r["geometry"] if r1_r else []))
            if t3 > 0.5:
                legs.append(_leg("walk", f"Transfer walk to {mid_bus['name']}", t3, d3, w2_r["geometry"] if w2_r else []))
            legs.append(_leg("ride", f"Bus {mid_bus['name']} → {d_bus['name']}", t4 + _BOARD_BUF_MIN, d4, r2_r["geometry"] if r2_r else []))
            if t5 > 0.5:
                legs.append(_leg("walk", f"Walk from {d_bus['name']}", t5, d5, w3_r["geometry"] if w3_r else []))

            plans.append({
                "label": "Rail + Bus", "tag": "Walk · Rail · Walk · Bus · Walk",
                "legs": legs, "total_min": total,
                "total_dist_mi": round(d1+d2+d3+d4+d5, 1), "transfers": 2,
            })

    # ── PLAN H: Drive to intercity coach terminal ─────────────────
    if nearby_intercity:
        t = nearby_intercity[0]  # nearest
        drv_r = osrm_route(olat, olon, t["lat"], t["lon"], "car")
        d_drv = _haversine(olat, olon, t["lat"], t["lon"])
        t_drv = _dur_from_route(drv_r, d_drv, _CAR_SPEED_MPH)
        # estimate intercity ride: straight-line / 55 mph (highway coach)
        t_ride = round(straight / 55 * 60, 1)
        total  = round(t_drv + 15 + t_ride, 1)   # 15 min check-in buffer
        carriers = ", ".join(t.get("carriers", []))
        plans.append({
            "label": "Intercity Coach",
            "tag":   f"{carriers} from {t['city']}",
            "legs": [
                _leg("car",   f"Drive to {t['city']} terminal", t_drv, d_drv,
                     drv_r["geometry"] if drv_r else [], t["city"]),
                _leg("coach", f"Coach {t['city']} → destination  (schedule varies)",
                     t_ride + 15, straight, [], t["city"]),
            ],
            "total_min": total,
            "total_dist_mi": round(d_drv + straight, 1),
            "transfers": 1,
        })

    # ── Rank & label ───────────────────────────────────────────────
    # Sort by total_min
    plans.sort(key=lambda p: p["total_min"])

    # Tag the fastest
    if plans:
        plans[0]["badge"] = "Fastest"

    # Tag fewest-transfers (excluding pure walk/drive which are 0)
    multi = [p for p in plans if p["transfers"] > 0]
    if multi:
        fewest = min(multi, key=lambda p: (p["transfers"], p["total_min"]))
        fewest.setdefault("badge", "Fewest transfers")

    # Tag most-walking (highest walk proportion)
    for p in plans:
        walk_min = sum(l["duration_min"] for l in p["legs"] if l["mode"] == "walk")
        p["_walk_pct"] = walk_min / max(p["total_min"], 1)
    walky = [p for p in plans if p["transfers"] > 0]
    if walky:
        most_walk = max(walky, key=lambda p: p["_walk_pct"])
        most_walk.setdefault("badge", "Most walking")

    # Clean internal key
    for p in plans:
        p.pop("_walk_pct", None)

    return plans


# Keep the old signatures as thin wrappers so build_map / comparison
# table code that references them still works without changes.
def build_transit_itinerary(olat, olon, dlat, dlon, origin_stops, dest_stops):
    """Legacy wrapper — returns the first walk·ride·walk plan or None."""
    plans = build_multimodal_options(olat, olon, dlat, dlon, origin_stops, dest_stops, [])
    for p in plans:
        if "Walk" in p.get("tag","") and "Rail" not in p.get("tag","") and p["transfers"] > 0:
            # repackage into the old shape so map rendering still works
            return {
                "legs": p["legs"], "total_min": p["total_min"],
                "total_dist_mi": p["total_dist_mi"],
                "origin_stop": {"name": p["legs"][0].get("stop","Stop"), "type":"Bus"},
                "dest_stop":   {"name": p["legs"][-1].get("stop","Stop"), "type":"Bus"},
                "steps": [l["label"] for l in p["legs"]],
            }
    return None

def build_combined_itinerary(olat, olon, dlat, dlon, origin_stops, dest_stops):
    """Legacy wrapper — returns the first drive·ride·walk plan or None."""
    plans = build_multimodal_options(olat, olon, dlat, dlon, origin_stops, dest_stops, [])
    for p in plans:
        if "Drive" in p.get("label","") and p["transfers"] > 0:
            return {
                "legs": p["legs"], "total_min": p["total_min"],
                "total_dist_mi": p["total_dist_mi"],
                "hub":       {"name": p["legs"][0].get("stop","Hub"), "type":"Bus Station"},
                "dest_stop": {"name": p["legs"][-1].get("stop","Stop"), "type":"Bus"},
                "steps": [l["label"] for l in p["legs"]],
            }
    return None


# ══════════════════════════════════════════════════════════════════════
# ROAD-INCIDENT FETCHERS  (nationwide)
# ══════════════════════════════════════════════════════════════════════
# Priority routing:
#   NC  → NC DOT TIMS  (live county incidents, no key)
#   CA  → Caltrans emergency closures via CA Open Data ArcGIS (no key)
#   WA  → WSDOT traveler-info incidents (no key)
#   ALL → Overpass: highway nodes/ways tagged construction / road_work /
#         access=no in a bounding-box around origin ↔ destination.
#         This fires for every state, including the three above, so the
#         user always gets OSM-sourced construction data as a layer.
# ══════════════════════════════════════════════════════════════════════

def _bbox_str(lat1, lon1, lat2, lon2, pad: float = 0.25) -> str:
    """south,west,north,east for Overpass / ArcGIS queries."""
    return (f"{min(lat1,lat2)-pad},{min(lon1,lon2)-pad},"
            f"{max(lat1,lat2)+pad},{max(lon1,lon2)+pad}")


# ── NC DOT TIMS ──────────────────────────────────────────────────────
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


# ── Caltrans emergency closures (CA Open Data ArcGIS — no key) ──────
@st.cache_data(ttl=180)
def fetch_caltrans_closures(olat, olon, dlat, dlon) -> List[Dict]:
    south = min(olat, dlat) - 0.3
    north = max(olat, dlat) + 0.3
    west  = min(olon, dlon) - 0.3
    east  = max(olon, dlon) + 0.3
    url   = ("https://gis.dot.ca.gov/arcgis/rest/services/Caltrans/"
             "Caltrans_Emergency_Road_Closures/FeatureServer/0/query")
    params = {
        "where": "1=1",
        "geometry": f"{west},{south},{east},{north}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "COUNTY,ROAD_NAME,CLOSURE_TYPE,DESCRIPTION,LATITUDE,LONGITUDE",
        "returnGeometry": "false",
        "f": "json",
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


# ── WSDOT traveler-info incidents (WA — no key) ─────────────────────
@st.cache_data(ttl=120)
def fetch_wsdot_incidents(olat, olon, dlat, dlon) -> List[Dict]:
    url = "https://wsdot.wa.gov/trafficapi/rest/Incident/Current"
    try:
        r = requests.get(url,
                         headers={"User-Agent": "WiDS-Caregiver-Alert/1.0"}, timeout=12)
        if r.status_code != 200:
            return []
        raw   = r.json()
        items = raw if isinstance(raw, list) else (raw.get("incidents") or raw.get("Incidents") or [])
        south, north = min(olat,dlat)-0.3, max(olat,dlat)+0.3
        west,  east  = min(olon,dlon)-0.3, max(olon,dlon)+0.3
        out = []
        for inc in items:
            lat = inc.get("Latitude") or inc.get("latitude")
            lon = inc.get("Longitude") or inc.get("longitude")
            if lat is None or lon is None:
                continue
            if not (south <= lat <= north and west <= lon <= east):
                continue
            out.append({
                "title":     inc.get("Description") or inc.get("description") or "Incident",
                "road":      inc.get("LocationDescription") or inc.get("Road") or "",
                "severity":  inc.get("Severity") or inc.get("severity") or "",
                "status":    inc.get("Status") or "Active",
                "latitude":  lat,
                "longitude": lon,
                "source":    "WSDOT",
            })
        return out
    except Exception:
        return []


# ── Overpass: construction / road-work / access=no  (universal) ──────
@st.cache_data(ttl=300)
def fetch_overpass_road_issues(olat, olon, dlat, dlon) -> List[Dict]:
    bb = _bbox_str(olat, olon, dlat, dlon, pad=0.2)
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
                lat  = elem.get("lat") or (elem.get("center") or {}).get("lat")
                lon  = elem.get("lon") or (elem.get("center") or {}).get("lon")
                if lat is None or lon is None:
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
                    "latitude": lat, "longitude": lon,
                    "source": "OpenStreetMap",
                })
            return out
        except Exception:
            continue
    return []


# ── Master dispatcher: picks the best source(s) for the detected state
def fetch_road_incidents(state: Optional[str], olat, olon, dlat, dlon,
                         origin_address: str) -> List[Dict]:
    """
    Returns a unified list of incident dicts.  State-specific feeds are
    tried first; Overpass construction tags are always appended so every
    route gets at least OSM-sourced data.
    """
    incidents: List[Dict] = []

    if state == "NC":
        county = CITY_TO_NC_COUNTY.get(
            origin_address.lower().strip().split(",")[0].strip())
        if county:
            incidents.extend(fetch_ncdot_incidents(county))
    elif state == "CA":
        incidents.extend(fetch_caltrans_closures(olat, olon, dlat, dlon))
    elif state == "WA":
        incidents.extend(fetch_wsdot_incidents(olat, olon, dlat, dlon))

    # Always layer on Overpass (works everywhere)
    incidents.extend(fetch_overpass_road_issues(olat, olon, dlat, dlon))
    return incidents


# ══════════════════════════════════════════════════════════════════════
# FIRE PROXIMITY  (checks corridor between origin and destination)
# ══════════════════════════════════════════════════════════════════════

def get_route_fires(olat, olon, dlat, dlon, fire_data, buffer_mi=20) -> List[Dict]:
    if fire_data is None or len(fire_data) == 0:
        return []
    # Sample 5 points along the O→D corridor
    sample_pts = [
        (olat, olon),
        ((olat * 3 + dlat) / 4, (olon * 3 + dlon) / 4),
        ((olat + dlat) / 2,     (olon + dlon) / 2),
        ((olat + dlat * 3) / 4, (olon + dlon * 3) / 4),
        (dlat, dlon),
    ]
    fires, seen = [], set()
    for _, fire in fire_data.iterrows():
        fl, flo = fire.get("latitude"), fire.get("longitude")
        if not fl or not flo:
            continue
        name = fire.get("fire_name", "Satellite Detection")
        if name in seen:
            continue
        min_d = min(_haversine(sp[0], sp[1], fl, flo) for sp in sample_pts)
        if min_d <= buffer_mi:
            seen.add(name)
            acres = fire.get("acres", 0)
            fires.append({
                "name": name, "lat": fl, "lon": flo,
                "acres": acres if (acres and acres == acres) else 0,
                "min_dist_mi": round(min_d, 1),
            })
    fires.sort(key=lambda x: x["min_dist_mi"])
    return fires


# ══════════════════════════════════════════════════════════════════════
# MAP BUILDER
# ══════════════════════════════════════════════════════════════════════

def _add_route_line(m, geom, mode_key, label, is_active):
    if not geom:
        return
    coords  = [[c[1], c[0]] for c in geom]
    weight  = 6 if is_active else 2
    opacity = 0.85 if is_active else 0.3
    colour  = MODE_COLOURS.get(mode_key, "#888")
    dash    = MODE_DASH.get(mode_key)
    kwargs  = dict(color=colour, weight=weight, opacity=opacity, tooltip=label)
    if dash:
        kwargs["dash_array"] = dash
    folium.PolyLine(coords, **kwargs).add_to(m)


def build_map(olat, olon, dlat, dlon,
              route_fires, incidents,
              origin_stops, dest_stops,
              origin_label, dest_label,
              intercity_terminals=None,
              active_plan=None,
              all_plans=None) -> folium.Map:
    """
    active_plan – the currently-selected plan's leg list (drawn bold)
    all_plans   – list of ALL plans; their legs are drawn faint underneath
    """
    mid_lat, mid_lon = (olat + dlat) / 2, (olon + dlon) / 2
    dist_mi = _haversine(olat, olon, dlat, dlon)
    zoom = 7 if dist_mi > 200 else (8 if dist_mi > 80 else (10 if dist_mi > 30 else 12))

    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=zoom, tiles="CartoDB positron")

    # OSM road overlay (subtle)
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="© OpenStreetMap contributors",
        name="OSM Roads",
        opacity=0.25,
    ).add_to(m)

    # ── Origin / Destination markers ──
    folium.Marker(
        [olat, olon],
        popup=f"<b>START</b><br>{origin_label}",
        icon=folium.Icon(color="green", icon="home", prefix="fa"),
        tooltip="Origin",
    ).add_to(m)
    folium.Marker(
        [dlat, dlon],
        popup=f"<b>DESTINATION</b><br>{dest_label}",
        icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
        tooltip="Destination",
    ).add_to(m)

    # ── Faint lines for every OTHER plan ──
    active_geoms = set()  # collect active geometries to skip in faint pass
    if active_plan:
        for leg in active_plan:
            g = leg.get("geometry")
            if g:
                active_geoms.add(id(g))

    if all_plans:
        for plan in all_plans:
            for leg in plan.get("legs", []):
                g = leg.get("geometry")
                if g and id(g) not in active_geoms:
                    _add_route_line(m, g, leg["mode"], leg["label"], False)

    # ── Bold active plan ──
    if active_plan:
        for leg in active_plan:
            _add_route_line(m, leg.get("geometry"), leg["mode"], leg["label"], True)

    # ── Transit-stop pins ──
    for stop in origin_stops[:15]:
        folium.CircleMarker(
            [stop["lat"], stop["lon"]], radius=6,
            color="#7c3aed", fill=True, fillColor="#a78bfa", fillOpacity=0.85,
            popup=f"<b>{stop['name']}</b><br>{stop['type']}<br>{stop.get('operator','')}",
            tooltip=f"{stop['type']}: {stop['name']}",
        ).add_to(m)
    for stop in dest_stops[:15]:
        folium.CircleMarker(
            [stop["lat"], stop["lon"]], radius=6,
            color="#7c3aed", fill=True, fillColor="#c4b5fd", fillOpacity=0.85,
            popup=f"<b>{stop['name']}</b><br>{stop['type']}<br>{stop.get('operator','')}",
            tooltip=f"{stop['type']}: {stop['name']}",
        ).add_to(m)

    # ── Intercity-bus terminal pins (teal diamonds) ──
    for t in (intercity_terminals or []):
        carriers = ", ".join(t.get("carriers", []))
        folium.Marker(
            [t["lat"], t["lon"]],
            icon=folium.DivIcon(
                html=f'<div style="font-size:18px;color:#0d9488;text-shadow:0 0 3px #fff;">'
                     f'◆</div>',
                icon_size=(20, 20), icon_anchor=(10, 10),
            ),
            popup=(f"<b>{t['city']}</b><br>"
                   f"<i>Intercity Coach</i><br>"
                   f"{carriers}<br>"
                   f"{t.get('address','')}<br>"
                   f"{t['dist_mi']} mi away"),
            tooltip=f"Coach: {t['city']} ({carriers})",
        ).add_to(m)

    # ── Fire circles ──
    for f in route_fires:
        acres = f.get("acres", 100) or 100
        folium.Circle(
            [f["lat"], f["lon"]],
            radius=max(int(acres * 40), 1000),
            color="red", fill=True, fillColor="orange", fillOpacity=0.35,
            popup=f"<b>{f['name']}</b><br>{f['min_dist_mi']} mi from route<br>{acres:,.0f} acres",
            tooltip=f"FIRE: {f['name']}",
        ).add_to(m)

    # ── Road-incident pins ──
    for inc in incidents[:8]:
        title = (inc.get("title") or inc.get("Title") or
                 inc.get("description") or inc.get("Description") or "Incident")
        sev   = inc.get("severity") or inc.get("Severity") or ""
        ilat  = inc.get("latitude") or inc.get("Latitude")
        ilon  = inc.get("longitude") or inc.get("Longitude")
        if ilat and ilon:
            folium.Marker(
                [float(ilat), float(ilon)],
                popup=f"<b>Road Incident</b><br>{title}<br>Severity: {sev}",
                icon=folium.Icon(color="orange", icon="exclamation-triangle", prefix="fa"),
                tooltip=f"Incident: {title}",
            ).add_to(m)

    # ── Legend ──
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
         background:white;padding:14px 18px;border-radius:10px;
         border:2px solid #ccc;font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,.25);
         font-family:sans-serif;">
     <b style="font-size:14px;">Legend</b><br><br>
     <span style="color:#2563eb;font-size:18px;">━━</span> Driving &nbsp;&nbsp;
     <span style="color:#16a34a;font-size:18px;">╌╌</span> Walking &nbsp;&nbsp;
     <span style="color:#9333ea;font-size:18px;">━━</span> Transit Ride<br><br>
     <span style="color:red;font-size:16px;">●</span> Fire Zone &nbsp;&nbsp;
     <span style="color:#7c3aed;font-size:14px;">●</span> Transit Stop &nbsp;&nbsp;
     <span style="color:#0d9488;font-size:14px;">◆</span> Intercity Coach &nbsp;&nbsp;
     <span style="color:orange;font-size:14px;">▲</span> Road Incident
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    return m


# ══════════════════════════════════════════════════════════════════════
# MAIN PAGE RENDERER
# ══════════════════════════════════════════════════════════════════════

def render_directions_page(fire_data, vulnerable_populations):
    """Entry point called by the multi-page dashboard."""

    st.title("Directions & Navigation")
    st.markdown(
        "Plan your route with real-time transit stops, fire-danger zones, "
        "and road-closure warnings — driving, walking, public transit, or a combined trip."
    )

    # ── session-state init ──
    for k, v in {
        "dir_origin": "", "dir_dest": "",
        "dir_origin_coords": None, "dir_dest_coords": None,
        "dir_triggered": False,
        "dir_origin_stops": None, "dir_dest_stops": None,
    }.items():
        st.session_state.setdefault(k, v)

    # ── Input row ──
    col_o, col_d, col_btn = st.columns([3, 3, 1])
    with col_o:
        origin_input = st.text_input("Origin", value=st.session_state.dir_origin,
                                     placeholder="e.g. Los Angeles, CA", key="dir_origin_input")
    with col_d:
        dest_input = st.text_input("Destination", value=st.session_state.dir_dest,
                                   placeholder="e.g. San Francisco, CA", key="dir_dest_input")
    with col_btn:
        go_btn = st.button("Get Directions", type="primary")

    if go_btn and origin_input.strip() and dest_input.strip():
        st.session_state.dir_origin = origin_input.strip()
        st.session_state.dir_dest   = dest_input.strip()
        st.session_state.dir_triggered = True
        st.session_state.dir_origin_coords = None
        st.session_state.dir_dest_coords   = None
        st.session_state.dir_origin_stops  = None
        st.session_state.dir_dest_stops    = None

    # ── Landing state ──
    if not st.session_state.dir_triggered:
        st.markdown("---")
        st.info(
            "Enter an origin and destination above, then click **Get Directions**.\n\n"
            "This planner shows real transit stops (OpenStreetMap), fires along your route, "
            "and live road-closure data (NC DOT, Caltrans, WSDOT, + OpenStreetMap everywhere). Routes come from the open-source OSRM engine."
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Driving", "OSRM car", "turn-by-turn")
        c2.metric("Walking", "OSRM foot", "step-by-step")
        c3.metric("Transit", "OSM stops", "walk+ride+walk")
        c4.metric("Combined", "Drive+Ride", "best of both")
        return

    # ── Geocode ──
    if st.session_state.dir_origin_coords is None:
        with st.spinner("Geocoding origin…"):
            st.session_state.dir_origin_coords = geocode(st.session_state.dir_origin)
    if st.session_state.dir_dest_coords is None:
        with st.spinner("Geocoding destination…"):
            st.session_state.dir_dest_coords = geocode(st.session_state.dir_dest)

    o_coords = st.session_state.dir_origin_coords
    d_coords = st.session_state.dir_dest_coords

    if not o_coords:
        st.error("Origin not found. Try 'City, State' format.")
        return
    if not d_coords:
        st.error("Destination not found. Try 'City, State' format.")
        return

    olat, olon = o_coords
    dlat, dlon = d_coords
    straight_mi = _haversine(olat, olon, dlat, dlon)

    c1, c2 = st.columns(2)
    c1.success(f"Origin: **{st.session_state.dir_origin.title()}**  ({olat:.4f}, {olon:.4f})")
    c2.success(f"Destination: **{st.session_state.dir_dest.title()}**  ({dlat:.4f}, {dlon:.4f})")
    st.caption(f"Straight-line distance: {straight_mi:.1f} mi")

    # ── Fetch transit stops ──
    if st.session_state.dir_origin_stops is None:
        with st.spinner("Finding transit stops near origin…"):
            st.session_state.dir_origin_stops = fetch_transit_stops(olat, olon)
    if st.session_state.dir_dest_stops is None:
        with st.spinner("Finding transit stops near destination…"):
            st.session_state.dir_dest_stops = fetch_transit_stops(dlat, dlon)

    origin_stops = st.session_state.dir_origin_stops or []
    dest_stops   = st.session_state.dir_dest_stops or []

    # ── Nearest intercity-bus terminals (static seed + any OSM coach stops) ──
    nearby_intercity = _nearest_intercity_terminals(olat, olon, INTERCITY_TERMINALS, n=5)
    # Also pull any Overpass-discovered intercity stops into the list
    for s in origin_stops:
        if s["type"] == "Intercity Coach" and not any(
                t["city"].lower().startswith(s["name"].lower()[:8]) for t in nearby_intercity):
            nearby_intercity.append({
                "city": s["name"], "lat": s["lat"], "lon": s["lon"],
                "carriers": [s.get("operator", "Coach")],
                "address": "", "dist_mi": round(_haversine(olat, olon, s["lat"], s["lon"]), 1),
            })
    nearby_intercity = sorted(nearby_intercity, key=lambda x: x["dist_mi"])[:6]

    # ── Compute all route plans (multimodal engine) ──
    with st.spinner("Calculating all route options…"):
        all_plans = build_multimodal_options(olat, olon, dlat, dlon,
                                            origin_stops, dest_stops,
                                            nearby_intercity)

    # Also grab the raw car route for turn-by-turn directions
    car_route = osrm_route(olat, olon, dlat, dlon, "car")

    # ── Fires along route ──
    route_fires = get_route_fires(olat, olon, dlat, dlon, fire_data, buffer_mi=20)

    # ── Road incidents (nationwide) ──
    state_o = _extract_state(st.session_state.dir_origin)
    with st.spinner("Checking road conditions…"):
        incidents = fetch_road_incidents(
            state_o, olat, olon, dlat, dlon, st.session_state.dir_origin)

    # ── Fire warning ──
    if route_fires:
        st.warning(
            f"**{len(route_fires)} active fire(s) detected along or near your route.**  "
            "Fire zones are shown on the map. Consider alternate routes if possible."
        )
        for f in route_fires[:4]:
            st.caption(f"  • {f['name']} — {f['min_dist_mi']} mi from route ({f['acres']:,.0f} acres)")

    # ── Road-incident advisory ──
    if incidents:
        src_groups: Dict[str, list] = {}
        for inc in incidents:
            src = inc.get("source", "Unknown")
            src_groups.setdefault(src, []).append(inc)
        st.warning(f"**{len(incidents)} road incident(s)** detected near your route.")
        for src, group in src_groups.items():
            st.caption(f"  Source: {src} — {len(group)} incident(s)")
            for inc in group[:3]:
                title = inc.get("title") or inc.get("Title") or inc.get("description") or "Incident"
                st.caption(f"    • {title}")
        state_abbr = _extract_state(st.session_state.dir_origin)
        dot = STATE_DOT_LINKS.get(state_abbr)
        if dot:
            st.caption(f"For full road conditions: [{dot['name']} DOT]({dot['url']}) • Call 511")

    # ── Session state for selected plan index ──
    if "dir_selected_plan" not in st.session_state:
        st.session_state.dir_selected_plan = 0
    # Clamp if plans changed
    if st.session_state.dir_selected_plan >= len(all_plans):
        st.session_state.dir_selected_plan = 0

    # ── COLOUR map for leg-bar badges ──
    LEG_COLOURS = {
        "car":   ("#2563eb", "#fff"),
        "walk":  ("#16a34a", "#fff"),
        "ride":  ("#9333ea", "#fff"),
        "coach": ("#0d9488", "#fff"),
    }

    # ── Two top-level tabs: Driving (turn-by-turn) | All Routes ──
    tab_drive, tab_routes = st.tabs(["Driving (turn-by-turn)", "All Route Options"])

    # ─── TAB: DRIVING (turn-by-turn) ────────────────────────────────
    with tab_drive:
        drive_plan = next((p for p in all_plans if p["label"] == "Drive"), None)
        drive_dur  = drive_plan["total_min"] if drive_plan else 0
        drive_dist = drive_plan["total_dist_mi"] if drive_plan else 0

        ca, cb = st.columns(2)
        ca.metric("Distance", f"{drive_dist} mi")
        cb.metric("ETA", _fmt(drive_dur))

        if car_route and car_route.get("steps"):
            st.markdown("**Turn-by-Turn**")
            for i, step in enumerate(car_route["steps"][:25], 1):
                st.write(f"{i}. {step}")
            if len(car_route["steps"]) > 25:
                st.caption(f"… and {len(car_route['steps']) - 25} more steps.")
        else:
            st.info("Turn-by-turn data unavailable from OSRM right now. Use the map below.")
        st.markdown("**Tips:** Check **511** or your state DOT for closures. Fill up gas. Carry water.")

        # Selecting this tab highlights the drive plan on the map
        drive_idx = next((i for i, p in enumerate(all_plans) if p["label"] == "Drive"), 0)
        st.session_state.dir_selected_plan = drive_idx

    # ─── TAB: ALL ROUTE OPTIONS (Google Maps-style cards) ──────────
    with tab_routes:
        st.caption(
            "Compare all available routes. Click a route to highlight it on the map below. "
            "Times are estimates — check carrier apps for live schedules."
        )

        for idx, plan in enumerate(all_plans):
            is_selected = (st.session_state.dir_selected_plan == idx)
            badge_text  = plan.get("badge", "")
            label       = plan["label"]
            total_min   = plan["total_min"]
            transfers   = plan["transfers"]

            # ── Card border styling ──
            border_color = "#2563eb" if is_selected else "#e2e8f0"
            border_width = "3px" if is_selected else "1px"

            st.markdown(
                f'<div style="border:{border_width} solid {border_color}; border-radius:12px; '
                f'padding:14px 16px; margin-bottom:10px; background:#{'f0f7ff' if is_selected else 'ffffff'};">',
                unsafe_allow_html=True,
            )

            # Header row: label + badge + time
            hcols = st.columns([3, 1, 1.5])
            hcols[0].markdown(f"**{label}**" + (f"  <span style='background:#2563eb;color:#fff;border-radius:4px;padding:1px 7px;font-size:12px;'>{badge_text}</span>" if badge_text else ""), unsafe_allow_html=True)
            hcols[1].markdown(f"<span style='color:#64748b;font-size:13px;'>{transfers} transfer{"s" if transfers != 1 else ""}</span>", unsafe_allow_html=True)
            hcols[2].markdown(f"<span style='font-weight:700;font-size:18px;'>{_fmt(total_min)}</span>", unsafe_allow_html=True)

            # ── Leg bar: coloured blocks proportional to time ──
            total_t = plan["total_min"] or 1
            bar_html = '<div style="display:flex;width:100%;height:28px;border-radius:6px;overflow:hidden;margin:8px 0;">'
            for leg in plan["legs"]:
                pct    = max(leg["duration_min"] / total_t * 100, 8)
                bg, fg = LEG_COLOURS.get(leg["mode"], ("#94a3b8", "#fff"))
                short  = leg["label"][:22] + "…" if len(leg["label"]) > 22 else leg["label"]
                bar_html += (
                    f'<div style="flex:{pct};background:{bg};color:{fg};'
                    f'display:flex;align-items:center;justify-content:center;'
                    f'font-size:11px;font-weight:600;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;'
                    f'padding:0 4px;" title="{leg['label']} — {_fmt(leg['duration_min'])}">'
                    f'{short}</div>'
                )
            bar_html += '</div>'
            st.markdown(bar_html, unsafe_allow_html=True)

            # ── Step list ──
            for leg in plan["legs"]:
                icon = {"car": "🚗", "walk": "🚶", "ride": "🚌", "coach": "🚌"}.get(leg["mode"], "•")
                st.caption(f"{icon}  {leg['label']}  —  {_fmt(leg['duration_min'])}  ({leg['dist_mi']} mi)")

            # Intercity coach booking links
            if any(l["mode"] == "coach" for l in plan["legs"]):
                t = nearby_intercity[0] if nearby_intercity else {}
                links = []
                for c in t.get("carriers", []):
                    cl = c.lower()
                    if "greyhound" in cl:  links.append("[Greyhound](https://www.greyhoundlines.com/en-us/)")
                    elif "flixbus" in cl:  links.append("[FlixBus](https://www.flixbus.com/)")
                    elif "megabus" in cl:  links.append("[Megabus](https://us.megabus.com/)")
                if links:
                    st.caption("Book:  " + "  •  ".join(links))

            # ── Select button ──
            if not is_selected:
                if st.button(f"Select this route", key=f"sel_plan_{idx}"):
                    st.session_state.dir_selected_plan = idx
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        st.warning(
            "Transit and coach times are estimates. Always check your local transit agency "
            "or carrier app for live schedules. Services may be suspended during emergencies."
        )

    # ── INTERACTIVE MAP ──
    st.markdown("---")
    st.subheader("Route Map")
    st.caption("Selected route is bold; other routes shown faint. Red = fire zones. Purple = transit stops. Teal ◆ = intercity coach.")

    selected_idx  = st.session_state.dir_selected_plan
    active_plan   = all_plans[selected_idx]["legs"] if all_plans else None

    m = build_map(
        olat, olon, dlat, dlon,
        route_fires=route_fires,
        incidents=incidents,
        origin_stops=origin_stops,
        dest_stops=dest_stops,
        origin_label=st.session_state.dir_origin.title(),
        dest_label=st.session_state.dir_dest.title(),
        intercity_terminals=nearby_intercity,
        active_plan=active_plan,
        all_plans=all_plans,
    )
    st_folium(m, width="100%", height=650, key="directions_route_map")


    # ── Emergency footer ──
    st.markdown("---")
    st.subheader("Emergency Resources")
    e1, e2, e3 = st.columns(3)
    e1.markdown("**Emergency Lines**\n- 911 — Fire / Police / Medical\n- 211 — Evacuation assistance\n- 511 — Road conditions\n- 988 — Crisis Lifeline")
    e2.markdown("**Before You Go**\n- Check road conditions (511)\n- Fill gas tank\n- Download offline maps\n- Carry water + snacks")
    e3.markdown("**Data Sources**\n- Routes: OSRM (open-source)\n- Stops: OpenStreetMap Overpass\n- Road issues: State DOTs + OSM\n- Map: OpenStreetMap / CartoDB")


# ── standalone test ──────────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(page_title="Directions & Navigation", layout="wide")
    render_directions_page(None, None)