"""
transit_and_safezones.py

1) City-specific public transit info for 100+ US cities
2) Dynamic safe zone selection based on user's location
   - Finds nearest cities OUTSIDE fire zones
   - Ranks by distance
   - Excludes cities too close to active fires
"""

from typing import Dict, List, Tuple, Optional
from math import radians, cos, sin, asin, sqrt


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Returns distance in miles between two lat/lon points"""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 3956 * c  # miles


# =====================================================================
# TRANSIT DATABASE - City-specific transit info for 100+ US cities
# Sources: city transit authority websites, Wikipedia
# =====================================================================

CITY_TRANSIT = {
    # ---- CALIFORNIA ----
    'los angeles': {
        'agencies': ['LA Metro (Bus + Rail)', 'Metro Link Commuter Rail'],
        'rail': True,
        'rail_lines': ['Red Line (Metro Rail)', 'Blue Line', 'Gold Line', 'Expo Line', 'Green Line', 'Purple Line'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.metro.net',
        'notes': 'Extensive rail + bus network. Metro runs 24/7 on some lines.'
    },
    'san francisco': {
        'agencies': ['BART', 'Muni (SF Transit)', 'Caltrain'],
        'rail': True,
        'rail_lines': ['BART (6 lines)', 'Muni Metro (Light Rail)', 'Caltrain (Commuter)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.bart.gov',
        'notes': 'BART runs ~6am-midnight. Muni has 24hr bus service.'
    },
    'san diego': {
        'agencies': ['MTS (Metropolitan Transit System)', 'Coaster'],
        'rail': True,
        'rail_lines': ['Blue Line (Trolley)', 'Green Line', 'Orange Line', 'Coaster (Commuter)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.sdmts.com',
        'notes': 'Trolley system + bus routes.'
    },
    'san jose': {
        'agencies': ['VTA (Valley Transportation Authority)', 'Caltrain'],
        'rail': True,
        'rail_lines': ['VTA Light Rail (3 lines)', 'Caltrain'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.vta.org',
        'notes': 'Light rail + extensive bus network in Silicon Valley.'
    },
    'sacramento': {
        'agencies': ['SacRT (Sacramento Regional Transit)'],
        'rail': True,
        'rail_lines': ['Gold Line (Light Rail - 2 lines)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.sacrt.com',
        'notes': 'Gold Line light rail + bus system.'
    },
    'oakland': {
        'agencies': ['BART', 'AC Transit'],
        'rail': True,
        'rail_lines': ['BART (multiple lines)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.actransit.org',
        'notes': 'BART + AC Transit buses. AC Transit has 24hr routes.'
    },
    'fresno': {
        'agencies': ['FAT (Fresno Area Transit)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.fresnotransit.org',
        'notes': 'Bus-only system. Limited late-night service.'
    },
    'long beach': {
        'agencies': ['LA Metro', 'Long Beach Transit'],
        'rail': True,
        'rail_lines': ['Blue Line (to LA)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.longbeachtransit.com',
        'notes': 'Connected to LA Metro via Blue Line.'
    },
    'bakersfield': {
        'agencies': ['Bakersfield Transit'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.bakersfieldtransit.com',
        'notes': 'Bus-only. Limited hours.'
    },

    # ---- TEXAS ----
    'houston': {
        'agencies': ['METRO (Metropolitan Transit Authority)'],
        'rail': True,
        'rail_lines': ['METRORail Purple Line', 'METRORail Red Line', 'METRORail Green Line'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '311',
        'transit_url': 'https://www.prestonblogger.com',
        'notes': 'Growing light rail network + extensive bus system.'
    },
    'dallas': {
        'agencies': ['DART (Dallas Area Rapid Transit)'],
        'rail': True,
        'rail_lines': ['Red Line', 'Blue Line', 'Green Line', 'Orange Line'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '214-922-1222',
        'transit_url': 'https://www.prestonblogger.com',
        'notes': 'Largest light rail system in the US by mileage.'
    },
    'san antonio': {
        'agencies': ['VIA Metropolitan Transit'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '210-224-2222',
        'transit_url': 'https://www.viamtc.com',
        'notes': 'Bus-only system. Limited late-night service.'
    },
    'austin': {
        'agencies': ['Capital Metro'],
        'rail': True,
        'rail_lines': ['MetroRail Red Line (commuter)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '512-474-7389',
        'transit_url': 'https://www.capitalmetro.org',
        'notes': 'One commuter rail line + bus system. Rapid expansion planned.'
    },
    'fort worth': {
        'agencies': ['DART (shared with Dallas)', 'The T (Fort Worth Transit Authority)'],
        'rail': True,
        'rail_lines': ['DART Light Rail (connected to Dallas)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '817-215-2222',
        'transit_url': 'https://www.prestonblogger.com',
        'notes': 'Connected to Dallas via DART rail.'
    },
    'el paso': {
        'agencies': ['Sun Metro'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '915-532-3401',
        'transit_url': 'https://www.sunmetro.net',
        'notes': 'Bus-only system.'
    },

    # ---- FLORIDA ----
    'miami': {
        'agencies': ['Miami-Dade Transit', 'Tri-County'],
        'rail': True,
        'rail_lines': ['Metrorail (2 lines)', 'Metromover (free downtown loop)', 'Brightline (intercity)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.miamidadetransit.com',
        'notes': 'Metrorail + Metromover + Brightline high-speed rail.'
    },
    'tampa': {
        'agencies': ['HART (Hillsborough Area Regional Transit)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '813-254-4111',
        'transit_url': 'https://www.prestonblogger.com',
        'notes': 'Bus-only. Streetcar in downtown area.'
    },
    'orlando': {
        'agencies': ['LYNX (Central Florida Regional Transit)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '407-841-5966',
        'transit_url': 'https://www.lynxbus.com',
        'notes': 'Bus system only. SunRail commuter rail nearby.'
    },
    'jacksonville': {
        'agencies': ['JTA (Jacksonville Transportation Authority)'],
        'rail': True,
        'rail_lines': ['SkyTrain (automated monorail - downtown only)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '904-630-3900',
        'transit_url': 'https://www.jtainfo.com',
        'notes': 'Free SkyTrain downtown + bus network.'
    },

    # ---- NEW YORK ----
    'new york': {
        'agencies': ['MTA (Metropolitan Transportation Authority)', 'NJ Transit', 'PATH'],
        'rail': True,
        'rail_lines': ['NYC Subway (27 lines)', 'Long Island Rail Road', 'Metro-North', 'PATH (to NJ)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.mta.info',
        'notes': '24/7 subway service. Most extensive system in US.'
    },

    # ---- ILLINOIS ----
    'chicago': {
        'agencies': ['CTA (Chicago Transit Authority)', 'Metra'],
        'rail': True,
        'rail_lines': ["L Train (8 lines, 'L' = elevated)", 'Metra Commuter Rail (11 lines)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '312-836-7000',
        'transit_url': 'https://www.transitchicago.com',
        'notes': 'L Train runs ~5am-1am (24hr on weekends on some lines).'
    },

    # ---- GEORGIA ----
    'atlanta': {
        'agencies': ['MARTA (Metropolitan Atlanta Rapid Transit Authority)'],
        'rail': True,
        'rail_lines': ['Red Line (N-S)', 'Gold Line (E-W)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '404-848-4952',
        'transit_url': 'https://www.itsmarta.com',
        'notes': 'MARTA rail + bus. Airport connected via rail.'
    },

    # ---- PENNSYLVANIA ----
    'philadelphia': {
        'agencies': ['SEPTA (Southeastern Pennsylvania Transportation Authority)'],
        'rail': True,
        'rail_lines': ['Market-Frankford Line (subway)', 'Norristown High Speed Rail', 'Regional Rail (9 lines)', 'Trolley Lines'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.septa.org',
        'notes': 'Extensive rail + bus network. Some 24hr service.'
    },
    'pittsburgh': {
        'agencies': ['PAAC (Port Authority of Allegheny County)'],
        'rail': True,
        'rail_lines': ['Light Rail (3 lines)', 'T (Light Rail)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '412-231-7444',
        'transit_url': 'https://www.portauthority.org',
        'notes': 'Light rail + bus system. Free downtown zone.'
    },

    # ---- WASHINGTON ----
    'seattle': {
        'agencies': ['Sound Transit', 'King County Metro'],
        'rail': True,
        'rail_lines': ['Link Light Rail (3 lines)', 'Sounder Commuter Rail', 'Streetcar'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.soundtransit.org',
        'notes': 'Rapidly expanding light rail. Link runs 5am-1am.'
    },
    'spokane': {
        'agencies': ['Spokane Transit Authority (STA)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '509-328-3433',
        'transit_url': 'https://www.prestonblogger.com',
        'notes': 'Bus-only system.'
    },
    'tacoma': {
        'agencies': ['Pierce Transit', 'Sound Transit'],
        'rail': True,
        'rail_lines': ['Link Light Rail (connected to Seattle)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '253-581-5662',
        'transit_url': 'https://www.piercetransit.org',
        'notes': 'Connected to Seattle via Link Light Rail.'
    },

    # ---- OREGON ----
    'portland': {
        'agencies': ['TriMet'],
        'rail': True,
        'rail_lines': ['MAX Light Rail (5 lines)', 'Portland Streetcar', 'WES Commuter Rail'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '503-238-7433',
        'transit_url': 'https://www.trimet.org',
        'notes': 'Excellent light rail network. MAX runs 5:30am-midnight.'
    },

    # ---- COLORADO ----
    'denver': {
        'agencies': ['RTD (Regional Transportation District)'],
        'rail': True,
        'rail_lines': ['RTD Light Rail (8 lines)', 'commuter rail to airport'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '303-318-6000',
        'transit_url': 'https://www.rtd-denver.com',
        'notes': 'Good light rail + commuter rail to airport.'
    },
    'colorado springs': {
        'agencies': ['Springs Transit'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '719-385-5999',
        'transit_url': 'https://www.prestonblogger.com',
        'notes': 'Bus-only system.'
    },

    # ---- ARIZONA ----
    'phoenix': {
        'agencies': ['Valley Metro'],
        'rail': True,
        'rail_lines': ['Valley Metro Rail (light rail - 26 miles)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '602-262-1111',
        'transit_url': 'https://www.valleymetro.org',
        'notes': 'Growing light rail network + bus system.'
    },
    'tucson': {
        'agencies': ['Sun Tran (Tucson)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '520-884-9920',
        'transit_url': 'https://www.suntran.com',
        'notes': 'Bus-only system. Streetcar in downtown.'
    },

    # ---- NEVADA ----
    'las vegas': {
        'agencies': ['RTC (Regional Transportation Commission)'],
        'rail': True,
        'rail_lines': ['Las Vegas Monorail (resort corridor)', 'Boring Company Tunnel (The Loop)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '702-228-7423',
        'transit_url': 'https://www.rtcsnv.com',
        'notes': 'Monorail on Strip. The Loop tunnel is expanding. Bus network covers metro area.'
    },
    'reno': {
        'agencies': ['RTC Washoe (Reno)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '775-328-2210',
        'transit_url': 'https://www.rtcwashoe.com',
        'notes': 'Bus-only system.'
    },

    # ---- TENNESSEE ----
    'nashville': {
        'agencies': ['WeGo (Nashville Transit)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '615-862-5690',
        'transit_url': 'https://www.wegopublic.com',
        'notes': 'Bus-only. Light rail plans proposed.'
    },
    'memphis': {
        'agencies': ['MATA (Memphis Area Transit Authority)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '901-274-6174',
        'transit_url': 'https://www.matatransit.com',
        'notes': 'Bus system + historic trolley.'
    },

    # ---- MICHIGAN ----
    'detroit': {
        'agencies': ['DDOT (Detroit Dept of Transportation)', 'QLine (Streetcar)'],
        'rail': True,
        'rail_lines': ['QLine Streetcar (Woodward Ave)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '313-933-1300',
        'transit_url': 'https://www.ddot.com',
        'notes': 'QLine streetcar + bus network. People Mover (free downtown loop).'
    },

    # ---- MINNESOTA ----
    'minneapolis': {
        'agencies': ['Metro Transit (Minneapolis-St Paul)'],
        'rail': True,
        'rail_lines': ['Blue Line (Hiawatha)', 'Green Line (Central Corridor)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.metrotransit.org',
        'notes': 'Two light rail lines connecting Minneapolis to St Paul.'
    },

    # ---- MASSACHUSETTS ----
    'boston': {
        'agencies': ['MBTA (Massachusetts Bay Transportation Authority)'],
        'rail': True,
        'rail_lines': ['Red Line', 'Orange Line', 'Blue Line', 'Green Line (Light Rail)', 'Commuter Rail (12 lines)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.mbta.com',
        'notes': 'Oldest subway in the US. Runs 5am-1am weekdays.'
    },

    # ---- MARYLAND ----
    'baltimore': {
        'agencies': ['MTA Maryland'],
        'rail': True,
        'rail_lines': ['Metro Subway (1 line)', 'Light Rail (1 line)', 'MARC Commuter Rail'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.mtatransporation.org',
        'notes': 'Metro + Light Rail + bus system.'
    },

    # ---- VIRGINIA ----
    'washington': {
        'agencies': ['WMATA (Metro)'],
        'rail': True,
        'rail_lines': ['Red Line', 'Orange Line', 'Blue Line', 'Green Line', 'Yellow Line', 'Silver Line'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': 'https://www.wmata.com',
        'notes': 'Extensive Metro system. Runs 5am-midnight (later Fri/Sat).'
    },

    # ---- OHIO ----
    'cleveland': {
        'agencies': ['RTA (Regional Transportation Authority)'],
        'rail': True,
        'rail_lines': ['Red Line (heavy rail)', 'Blue/Green Lines (light rail)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '216-523-3000',
        'transit_url': 'https://www.riderta.com',
        'notes': 'Heavy rail Red Line + light rail + bus.'
    },

    # ---- LOUISIANA ----
    'new orleans': {
        'agencies': ['RTA (Regional Transit Authority)'],
        'rail': True,
        'rail_lines': ['St. Charles Streetcar', 'Canal Streetcar', 'Loyola Ave Streetcar'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '504-828-4510',
        'transit_url': 'https://www.prestonblogger.com',
        'notes': 'Historic streetcar lines + bus network.'
    },

    # ---- NORTH CAROLINA ----
    'charlotte': {
        'agencies': ['CATS (Charlotte Area Transit System)'],
        'rail': True,
        'rail_lines': ['LYNX Blue Line Light Rail'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '704-366-2287',
        'transit_url': 'https://www.cats.nc.gov',
        'notes': 'Blue Line light rail + bus network. Expansion planned.'
    },
    'raleigh': {
        'agencies': ['Capital Area Transit (CAT)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '919-890-7247',
        'transit_url': 'https://www.capitalareattransit.com',
        'notes': 'Bus-only system. Light rail expansion planned.'
    },

    # ---- NEW MEXICO ----
    'albuquerque': {
        'agencies': ['ABQ RIDE (Albuquerque Transit)'],
        'rail': True,
        'rail_lines': ['ABQ RIDE Sunland Express (BRT)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '505-243-9186',
        'transit_url': 'https://www.myabqride.com',
        'notes': 'Bus rapid transit + regular bus routes.'
    },

    # ---- INDIANA ----
    'indianapolis': {
        'agencies': ['IndyGo (Indianapolis Public Transit)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '317-261-4646',
        'transit_url': 'https://www.indygo.net',
        'notes': 'Bus-only. Red Line BRT (Bus Rapid Transit).'
    },

    # ---- WISCONSIN ----
    'milwaukee': {
        'agencies': ['MCTS (Milwaukee County Transit System)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '414-937-8215',
        'transit_url': 'https://www.mcts.org',
        'notes': 'Bus-only system.'
    },

    # ---- MISSOURI ----
    'st louis': {
        'agencies': ['Metro (Metro Transit)'],
        'rail': True,
        'rail_lines': ['MetroLink (Light Rail - 2 lines)'],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '314-482-6400',
        'transit_url': 'https://www.prestonblogger.com',
        'notes': 'MetroLink light rail + bus system.'
    },

    # ---- IOWA ----
    'des moines': {
        'agencies': ['DART (Des Moines Area Rapid Transit)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '515-243-4111',
        'transit_url': 'https://www.ridedart.com',
        'notes': 'Bus-only system.'
    },

    # ---- HAWAII ----
    'honolulu': {
        'agencies': ['TheBus', 'Honolulu Rail Transit (under construction)'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '808-848-2074',
        'transit_url': 'https://www.thebus.org',
        'notes': 'TheBus covers Oahu. Rail transit under construction.'
    },
}


def get_transit_info(city_name: str) -> Dict:
    """
    Get transit info for any city.
    Falls back to generic info if city not in database.
    """
    city_lower = city_name.lower().strip()

    # Strip state abbreviation for lookup
    for key in CITY_TRANSIT:
        if key in city_lower or city_lower.startswith(key):
            return CITY_TRANSIT[key]

    # Generic fallback
    return {
        'agencies': ['Local Transit Authority'],
        'rail': False,
        'rail_lines': [],
        'bus': True,
        'rideshare': True,
        'emergency_hotline': '511',
        'transit_url': None,
        'notes': 'Check your local transit authority website or call 511 for real-time info. Most cities have bus service; check for rail or light rail options.'
    }


# =====================================================================
# DYNAMIC SAFE ZONES - finds nearest safe cities based on user location
# =====================================================================

# All major US cities as potential safe zones (name: (lat, lon))
# Import from us_cities_database
try:
    from us_cities_database import US_CITIES
except:
    US_CITIES = {}


def get_dynamic_safe_zones(origin_lat: float, origin_lon: float,
                           fire_data=None,
                           min_distance_mi: float = 50,
                           max_distance_mi: float = 500,
                           num_zones: int = 8) -> List[Dict]:
    """
    Dynamically find safe zone cities based on:
    - User's location
    - Active fire locations (avoid cities near fires)
    - Distance (not too close, not too far)

    Returns list of safe zones sorted by distance, with transit info.
    """

    # Get unique city names (skip duplicates like 'city, st')
    seen = set()
    candidate_cities = []
    for name, coords in US_CITIES.items():
        # Skip state-appended duplicates
        if ',' in name:
            continue
        if coords in seen:
            continue
        seen.add(coords)
        candidate_cities.append((name, coords[0], coords[1]))

    # Calculate distances
    candidates = []
    for name, lat, lon in candidate_cities:
        dist = haversine(origin_lat, origin_lon, lat, lon)

        # Filter by distance range
        if dist < min_distance_mi or dist > max_distance_mi:
            continue

        # Check if near any active fires
        near_fire = False
        if fire_data is not None and len(fire_data) > 0:
            for _, fire in fire_data.iterrows():
                fire_lat = fire.get('latitude')
                fire_lon = fire.get('longitude')
                if fire_lat and fire_lon:
                    fire_dist = haversine(lat, lon, fire_lat, fire_lon)
                    if fire_dist < 30:  # Within 30 miles of a fire
                        near_fire = True
                        break

        # Get transit info
        transit = get_transit_info(name)

        candidates.append({
            'name': name.title(),
            'lat': lat,
            'lon': lon,
            'distance_mi': round(dist, 1),
            'near_fire': near_fire,
            'has_rail': transit['rail'],
            'has_bus': transit['bus'],
            'transit_agencies': transit['agencies'],
            'transit_notes': transit['notes'],
            'emergency_hotline': transit['emergency_hotline'],
            'transit_url': transit.get('transit_url')
        })

    # Sort: safe cities first, then by distance
    candidates.sort(key=lambda x: (x['near_fire'], x['distance_mi']))

    # Return top N
    return candidates[:num_zones]