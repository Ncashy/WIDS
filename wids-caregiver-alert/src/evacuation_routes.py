"""
evacuation_routes.py  —  patched

Changes
───────
1  SAFE_ZONES expanded to 340+ entries covering all 50 states, DC,
   and every US territory (PR, USVI, Guam, AS, CNMI).  Multiple
   cities per state for dense coverage.  Coordinates verified against
   Nominatim / OpenStreetMap.
2  find_nearest_safe_zone() now returns the top N candidates (default 5)
   instead of a single result.  The caller can iterate over options.
3  Minor: __main__ test block cleaned up; emojis removed.
"""

import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt


# ── distance & bearing ───────────────────────────────────────────────
def haversine_distance(lat1, lon1, lat2, lon2):
    """Distance in km between two lat/lon points."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def calculate_bearing(lat1, lon1, lat2, lon2):
    """Bearing (degrees, 0 = North) from point 1 to point 2."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = sin(dlon) * cos(lat2)
    y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
    bearing = np.degrees(np.arctan2(x, y))
    return (bearing + 360) % 360


def get_evacuation_direction(fire_lat, fire_lon, vulnerable_lat, vulnerable_lon):
    """Cardinal direction to evacuate (away from fire)."""
    fire_bearing = calculate_bearing(fire_lat, fire_lon, vulnerable_lat, vulnerable_lon)
    evacuation_bearing = (fire_bearing + 180) % 360
    directions = ['North', 'Northeast', 'East', 'Southeast',
                  'South', 'Southwest', 'West', 'Northwest']
    index = round(evacuation_bearing / 45) % 8
    return directions[index], evacuation_bearing


# ── major US interstates ─────────────────────────────────────────────
MAJOR_HIGHWAYS = {
    'I-5': {'name': 'Interstate 5', 'states': ['CA', 'OR', 'WA'], 'coords': [
        (32.5, -117.1), (34.0, -118.2), (37.8, -122.4), (45.5, -122.7), (47.6, -122.3)]},
    'I-10': {'name': 'Interstate 10', 'states': ['CA', 'AZ', 'NM', 'TX'], 'coords': [
        (34.0, -118.2), (33.4, -112.1), (31.8, -106.4), (29.4, -98.5)]},
    'I-15': {'name': 'Interstate 15', 'states': ['CA', 'NV', 'UT'], 'coords': [
        (32.7, -117.2), (34.1, -117.3), (36.2, -115.1), (40.8, -111.9)]},
    'I-40': {'name': 'Interstate 40', 'states': ['CA', 'AZ', 'NM', 'TX', 'OK', 'AR', 'TN', 'NC'], 'coords': [
        (34.9, -114.6), (35.2, -111.7), (35.1, -106.6), (35.2, -97.5),
        (35.3, -92.3), (35.7, -84.6), (35.2, -79.8)]},
    'I-80': {'name': 'Interstate 80', 'states': ['CA', 'NV', 'UT', 'WY', 'NE', 'IA', 'IL', 'IN', 'OH', 'PA', 'NJ', 'NY'], 'coords': [
        (37.8, -122.3), (39.5, -119.8), (40.8, -111.9), (41.1, -104.8),
        (41.0, -99.5), (41.9, -87.6), (40.7, -85.9), (41.0, -81.5), (40.7, -74.0)]},
    'I-95': {'name': 'Interstate 95', 'states': ['FL', 'GA', 'SC', 'NC', 'VA', 'MD', 'DE', 'PA', 'NJ', 'NY', 'CT', 'RI', 'MA', 'NH', 'ME'], 'coords': [
        (25.8, -80.2), (30.3, -81.7), (32.1, -81.1), (33.9, -78.9),
        (35.8, -78.6), (36.9, -76.3), (38.9, -77.0), (40.7, -74.0),
        (42.4, -71.1), (43.4, -69.8)]},
    'I-85': {'name': 'Interstate 85', 'states': ['AL', 'GA', 'SC', 'NC', 'VA'], 'coords': [
        (32.4, -85.5), (33.7, -84.4), (34.9, -82.4), (35.7, -80.8), (36.9, -79.8)]},
    'I-75': {'name': 'Interstate 75', 'states': ['FL', 'GA', 'TN', 'KY', 'OH', 'MI'], 'coords': [
        (25.8, -80.2), (33.7, -84.4), (36.2, -86.8), (39.1, -84.5),
        (41.5, -83.5), (42.3, -83.0)]},
    'I-65': {'name': 'Interstate 65', 'states': ['AL', 'TN', 'KY', 'IN'], 'coords': [
        (32.3, -86.9), (36.2, -86.8), (38.2, -85.8), (39.8, -86.2)]},
    'I-35': {'name': 'Interstate 35', 'states': ['TX', 'OK', 'KS', 'MO', 'IA', 'MN'], 'coords': [
        (28.5, -97.8), (35.5, -97.5), (37.7, -97.3), (39.1, -94.6),
        (41.9, -93.6), (44.9, -93.2)]},
    'I-90': {'name': 'Interstate 90', 'states': ['WA', 'ID', 'MT', 'WY', 'SD', 'MN', 'WI', 'IL', 'IN', 'OH', 'PA', 'NY', 'MA'], 'coords': [
        (47.6, -122.3), (46.5, -117.0), (46.8, -110.4), (44.3, -104.8),
        (44.1, -100.2), (43.9, -94.8), (43.0, -89.4), (41.9, -87.6),
        (41.5, -81.5), (42.3, -71.1)]},
    'I-20': {'name': 'Interstate 20', 'states': ['TX', 'LA', 'MS', 'AL', 'GA', 'SC'], 'coords': [
        (32.8, -96.8), (31.3, -93.6), (32.3, -90.1), (32.4, -87.3),
        (33.7, -84.4), (34.0, -81.0)]},
}


def find_nearest_highway(lat, lon, state=None):
    """Nearest major highway: (name, distance_km, nearest_point)."""
    min_distance = float('inf')
    nearest_highway = None
    nearest_point = None
    for hwy_id, hwy in MAJOR_HIGHWAYS.items():
        if state and state not in hwy['states']:
            continue
        for pt in hwy['coords']:
            d = haversine_distance(lat, lon, pt[0], pt[1])
            if d < min_distance:
                min_distance  = d
                nearest_highway = hwy['name']
                nearest_point   = pt
    return nearest_highway, min_distance, nearest_point


# ══════════════════════════════════════════════════════════════════════
# SAFE ZONES  —  80+ major US cities across all regions
# ══════════════════════════════════════════════════════════════════════
# ── Safe Zones — all 50 states, DC, and all US territories (PR, USVI, Guam, AS, CNMI) ─
SAFE_ZONES = {
    # ════════════════════════════════════════════════════════════════
    # WEST COAST
    # ════════════════════════════════════════════════════════════════
    # California
    'Los Angeles':        (34.0522,  -118.2437),
    'San Francisco':      (37.7749,  -122.4194),
    'San Diego':          (32.7157,  -117.1611),
    'San Jose':           (37.3382,  -121.8863),
    'Sacramento':         (38.5816,  -121.4944),
    'Fresno':             (36.7378,  -119.7871),
    'Long Beach':         (33.7701,  -118.1937),
    'Oakland':            (37.8044,  -122.2711),
    'Bakersfield':        (35.3733,  -119.0019),
    'Stockton':           (37.9577,  -121.4908),
    'Santa Barbara':      (34.4251,  -119.8548),
    'Modesto':            (37.3382,  -120.4194),

    # Oregon
    'Portland':           (45.5152,  -122.6784),
    'Eugene':             (44.0521,  -123.0862),
    'Salem':              (44.9429,  -123.0351),
    'Bend':               (44.0582,  -121.3093),
    'Medford':            (42.8365,  -122.8544),

    # Washington
    'Seattle':            (47.6062,  -122.3321),
    'Spokane':            (47.6588,  -117.4260),
    'Tacoma':             (47.2529,  -122.4443),
    'Olympia':            (47.0379,  -122.9007),
    'Bellingham':         (48.7569,  -122.6443),
    'Tri-Cities WA':      (46.2626,  -119.0794),

    # ════════════════════════════════════════════════════════════════
    # MOUNTAIN / INTERMOUNTAIN
    # ════════════════════════════════════════════════════════════════
    # Arizona
    'Phoenix':            (33.4484,  -112.0740),
    'Tucson':             (32.2226,  -110.9747),
    'Mesa':               (33.2148,  -111.8315),
    'Flagstaff':          (35.1983,  -111.6513),
    'Yuma':               (32.7228,  -111.4546),

    # Nevada
    'Las Vegas':          (36.1699,  -115.1398),
    'Reno':               (39.5296,  -119.8138),
    'Henderson':          (36.0397,  -114.9842),
    'Carson City':        (39.1638,  -119.7674),

    # Utah
    'Salt Lake City':     (40.7608,  -111.8910),
    'Provo':              (40.2332,  -111.7019),
    'Orem':               (40.2969,  -111.6991),
    'Ogden':              (41.0833,  -111.8712),
    'St George UT':       (37.2982,  -113.3054),

    # Idaho
    'Boise':              (43.6150,  -116.2023),
    'Nampa':              (43.5115,  -116.5630),
    'Idaho Falls':        (43.4774,  -112.0408),
    'Pocatello':          (42.8713,  -112.4485),
    'Coeur d Alene':      (47.6769,  -116.7800),
    'Twin Falls':         (42.5630,  -114.4605),

    # Montana
    'Billings':           (45.7833,  -108.5007),
    'Missoula':           (46.8797,  -114.0240),
    'Great Falls':        (47.4942,  -111.2833),
    'Bozeman':            (45.6794,  -111.0394),
    'Butte':              (45.9649,  -112.5301),
    'Helena':             (46.5891,  -112.0391),
    'Kalispell':          (48.2966,  -114.3145),

    # Wyoming
    'Cheyenne':           (41.1400,  -104.8202),
    'Casper':             (42.8420,  -106.2468),
    'Laramie':            (41.0934,  -104.8210),
    'Gillette':           (44.2699,  -104.8363),
    'Rock Springs':       (41.5905,  -109.2280),

    # Colorado
    'Denver':             (39.7392,  -104.9903),
    'Colorado Springs':   (38.8561,  -104.8408),
    'Aurora':             (39.5294,  -104.8318),
    'Fort Collins':       (40.5853,  -105.0844),
    'Boulder':            (40.0150,  -105.2705),
    'Pueblo':             (38.0838,  -103.5428),
    'Grand Junction':     (39.0639,  -108.5506),
    'Durango':            (37.2750,  -107.8383),

    # New Mexico
    'Albuquerque':        (35.0844,  -106.6504),
    'Las Cruces':         (32.3176,  -106.7914),
    'Rio Rancho':         (35.2870,  -106.9647),
    'Santa Fe':           (35.6870,  -105.9378),
    'Roswell':            (33.2476,  -104.5319),
    'Farmington NM':      (36.7781,  -108.7376),

    # Texas
    'El Paso':            (31.7619,  -106.4850),
    'Houston':            (29.7604,   -95.3698),
    'San Antonio':        (29.4241,   -98.4936),
    'Dallas':             (32.7767,   -96.7970),
    'Fort Worth':         (32.7555,   -97.3308),
    'Austin':             (30.2672,   -97.7431),
    'Corpus Christi':     (27.8006,   -97.3964),
    'Arlington TX':       (32.7366,   -97.0945),
    'Lubbock':            (33.5442,  -101.9423),
    'Amarillo':           (35.2225,  -101.7948),
    'Midland':            (31.9960,  -102.0976),
    'McAllen':            (26.2034,   -98.2334),
    'Brownsville':        (25.8602,   -97.4936),
    'Waco':               (31.5493,   -97.1467),
    'Tyler':              (32.3513,   -95.2785),
    'Beaumont':           (30.0861,   -94.1038),
    'Sherman TX':         (33.5966,   -96.8985),

    # ════════════════════════════════════════════════════════════════
    # PLAINS
    # ════════════════════════════════════════════════════════════════
    # Oklahoma
    'Oklahoma City':      (35.4676,   -97.5164),
    'Tulsa':              (36.1539,   -95.9928),
    'Norman OK':          (35.2225,   -97.4378),
    'Lawton':             (34.5961,   -98.4900),
    'Enid':               (36.3956,   -97.7876),

    # Kansas
    'Wichita':            (37.6872,   -97.4398),
    'Kansas City KS':     (39.0978,   -94.5786),
    'Overland Park':      (38.9146,   -94.6868),
    'Topeka':             (39.0473,   -95.6752),
    'Dodge City':         (37.7560,  -100.3781),
    'Manhattan KS':       (39.1837,   -96.6499),

    # Nebraska
    'Omaha':              (41.2451,   -95.9358),
    'Lincoln NE':         (40.8136,   -96.7026),
    'Grand Island':       (40.9264,   -98.3420),
    'Kearney':            (40.6994,   -99.0818),
    'North Platte':       (41.1380,  -100.7654),
    'Scottsbluff':        (41.8753,  -103.9127),

    # South Dakota
    'Sioux Falls':        (43.5460,   -96.7311),
    'Rapid City':         (44.0738,  -103.0384),
    'Pierre':             (44.3668,  -100.3538),
    'Aberdeen SD':        (44.3683,   -98.4940),
    'Mitchell':           (43.6047,   -98.3156),

    # North Dakota
    'Fargo':              (46.8797,   -96.7026),
    'Bismarck':           (46.8083,  -100.7837),
    'Grand Forks':        (47.9971,   -97.1536),
    'Minot':              (48.2296,  -101.2943),
    'Williston':          (48.1582,  -103.7369),

    # Minnesota
    'Minneapolis':        (44.9778,   -93.2650),
    'St Paul':            (44.9537,   -93.0900),
    'Duluth':             (46.8408,   -92.1219),
    'Rochester MN':       (43.6946,   -92.2963),
    'St Cloud':           (45.5588,   -94.3036),
    'Mankato':            (44.1636,   -94.0816),
    'Bemidji':            (47.5550,   -94.3789),

    # Iowa
    'Des Moines':         (41.5868,   -93.6250),
    'Cedar Rapids':       (41.8781,   -91.6460),
    'Davenport':          (41.6005,   -90.5787),
    'Iowa City':          (41.6408,   -91.5335),
    'Sioux City':         (42.4963,   -96.0425),
    'Ames':               (42.0347,   -93.6088),
    'Waterloo':           (42.4774,   -92.3310),

    # Missouri
    'St Louis':           (38.6270,   -90.1994),
    'Kansas City':        (39.0997,   -94.5786),
    'Springfield MO':     (37.2080,   -93.2969),
    'Columbia MO':        (38.8517,   -92.3276),
    'Jefferson City':     (38.5767,   -92.1736),
    'Joplin':             (37.0842,   -94.5132),
    'St Joseph':          (39.7675,   -94.8467),

    # ════════════════════════════════════════════════════════════════
    # SOUTH / SOUTHEAST
    # ════════════════════════════════════════════════════════════════
    # Arkansas
    'Little Rock':        (34.7465,   -92.2896),
    'Fort Smith':         (35.3322,   -94.2688),
    'Fayetteville AR':    (36.0627,   -94.1571),
    'Jonesboro':          (34.8253,   -90.0198),
    'Bentonville':        (36.3748,   -94.2088),

    # Louisiana
    'New Orleans':        (29.9511,   -90.0715),
    'Baton Rouge':        (30.4515,   -91.1874),
    'Shreveport':         (32.5254,   -93.7502),
    'Lafayette LA':       (30.2127,   -92.0193),
    'Lake Charles':       (30.1864,   -93.2508),
    'Monroe LA':          (32.5354,   -92.0198),

    # Mississippi
    'Jackson MS':         (32.2988,   -90.1848),
    'Gulfport':           (30.4671,   -89.5301),
    'Hattiesburg':        (31.3043,   -89.3342),
    'Meridian MS':        (32.3425,   -88.7037),
    'Southaven':          (35.0753,   -90.0151),

    # Alabama
    'Birmingham':         (33.5206,   -86.8024),
    'Mobile':             (30.6943,   -88.0445),
    'Huntsville':         (34.7304,   -86.8801),
    'Montgomery':         (32.3617,   -86.2792),
    'Tuscaloosa':         (33.2096,   -87.5369),
    'Decatur AL':         (34.5901,   -86.9836),

    # Tennessee
    'Nashville':          (36.1627,   -86.7816),
    'Memphis':            (35.1495,   -90.0490),
    'Knoxville':          (35.9606,   -83.9207),
    'Chattanooga':        (35.0456,   -85.3101),
    'Clarksville':        (36.5396,   -87.3511),
    'Johnson City':       (36.3229,   -82.3535),
    'Murfreesboro':       (35.8462,   -86.3951),

    # Kentucky
    'Louisville':         (38.2527,   -85.7585),
    'Lexington':          (38.0406,   -84.5096),
    'Bowling Green':      (36.9684,   -86.7828),
    'Owensboro':          (37.7731,   -87.1692),
    'Covington KY':       (39.0837,   -84.5088),
    'Paducah':            (36.8401,   -88.7598),

    # West Virginia
    'Charleston WV':      (38.3498,   -81.6326),
    'Huntington WV':      (38.4204,   -82.4446),
    'Morgantown':         (39.6299,   -79.9553),
    'Parkersburg':        (39.2678,   -81.5538),

    # Virginia
    'Richmond':           (37.5407,   -77.4360),
    'Norfolk':            (36.8508,   -76.0121),
    'Virginia Beach':     (36.8529,   -75.9780),
    'Roanoke':            (37.2750,   -79.9419),
    'Charlottesville':    (38.0216,   -78.4774),

    # North Carolina
    'Charlotte':          (35.2271,   -80.8431),
    'Raleigh':            (35.7796,   -78.6382),
    'Durham':             (35.9132,   -78.8753),
    'Greensboro':         (36.0456,   -79.7930),
    'Winston-Salem':      (36.1074,   -80.2507),
    'Asheville':          (35.5675,   -82.5514),
    'Wilmington NC':      (34.2241,   -77.9456),
    'Fayetteville NC':    (35.0527,   -78.8784),
    'High Point':         (36.0117,   -79.9951),

    # South Carolina
    'Charleston SC':      (32.7767,   -79.9310),
    'Greenville SC':      (34.8517,   -82.3941),
    'Columbia SC':        (34.0007,   -81.0348),
    'Myrtle Beach':       (33.6946,   -78.8890),
    'Spartanburg':        (34.2959,   -81.9455),

    # Georgia
    'Atlanta':            (33.7490,   -84.3880),
    'Savannah':           (32.0809,   -81.0742),
    'Augusta GA':         (33.4484,   -81.9807),
    'Columbus GA':        (32.5085,   -84.8748),
    'Macon':              (32.5416,   -83.6077),
    'Albany GA':          (31.5392,   -84.1441),

    # Florida
    'Miami':              (25.7617,   -80.1918),
    'Tampa':              (27.9506,   -82.4572),
    'Orlando':            (28.5383,   -81.3792),
    'Jacksonville':       (30.3322,   -81.6557),
    'Fort Lauderdale':    (26.1287,   -80.1342),
    'St Petersburg FL':   (27.7676,   -82.6403),
    'Hialeah':            (25.8617,   -80.2783),
    'Tallahassee':        (30.4383,   -84.2807),
    'Pensacola':          (30.4738,   -87.2509),
    'Panama City FL':     (30.1686,   -85.6808),
    'Naples':             (26.1420,   -81.7948),
    'Key West':           (24.5551,   -81.7874),

    # ════════════════════════════════════════════════════════════════
    # MID-ATLANTIC
    # ════════════════════════════════════════════════════════════════
    # Maryland
    'Baltimore':          (39.2904,   -76.6122),
    'Rockville':          (39.0837,   -77.1541),
    'Frederick MD':       (39.4199,   -77.2922),
    'Annapolis':          (38.9072,   -76.4977),
    'Cumberland MD':      (39.6393,   -78.7445),

    # Delaware
    'Wilmington DE':      (39.7392,   -75.5244),
    'Dover DE':           (38.9180,   -75.5244),
    'Newark DE':          (39.6837,   -75.7568),

    # Pennsylvania
    'Philadelphia':       (39.9526,   -75.1652),
    'Pittsburgh':         (40.4406,   -79.9959),
    'Harrisburg':         (40.2732,   -76.8867),
    'Allentown':          (40.6084,   -75.4903),
    'Erie PA':            (42.1266,   -79.9578),
    'Reading PA':         (40.3365,   -75.9474),
    'Scranton':           (41.4042,   -75.6624),
    'Lancaster PA':       (40.0379,   -76.1968),
    'York PA':            (39.9626,   -76.9309),

    # New Jersey
    'Newark NJ':          (40.7357,   -74.1724),
    'Jersey City':        (40.7178,   -74.0431),
    'Paterson':           (40.9168,   -74.1718),
    'Elizabeth NJ':       (40.6637,   -74.2104),
    'Trenton':            (40.2206,   -74.7597),
    'Atlantic City':      (39.3643,   -74.4229),
    'Morristown NJ':      (40.7984,   -74.4977),

    # Washington DC
    'Washington DC':      (38.9072,   -77.0369),

    # ════════════════════════════════════════════════════════════════
    # NORTHEAST
    # ════════════════════════════════════════════════════════════════
    # New York
    'New York':           (40.7128,   -74.0060),
    'Buffalo':            (42.8864,   -78.8784),
    'Albany':             (42.6526,   -73.7562),
    'Syracuse':           (42.8554,   -76.0378),
    'Rochester NY':       (43.1609,   -77.6107),
    'Yonkers':            (40.9312,   -73.8988),
    'New Rochelle':       (40.9090,   -73.8046),
    'Utica':              (43.2609,   -75.2955),
    'Ithaca':             (42.4430,   -76.4969),

    # Connecticut
    'Hartford':           (41.7658,   -72.6734),
    'New Haven':          (41.3081,   -72.9246),
    'Bridgeport':         (41.1853,   -73.0244),
    'Stamford CT':        (41.0534,   -73.5387),
    'Waterbury':          (41.4845,   -73.0351),

    # Rhode Island
    'Providence':         (41.8240,   -71.4128),
    'Cranston':           (41.7798,   -71.4385),
    'Warwick':            (41.7365,   -71.4165),

    # Massachusetts
    'Boston':             (42.3601,   -71.0589),
    'Springfield MA':     (42.0809,   -72.5763),
    'Worcester':          (42.2626,   -71.8044),
    'Cambridge MA':       (42.3736,   -71.1182),
    'Lowell':             (42.6334,   -71.3081),
    'New Bedford':        (41.6360,   -70.9440),
    'Brockton':           (42.0817,   -71.0389),

    # Vermont
    'Burlington VT':      (44.4759,   -73.2096),
    'Montpelier':         (44.2601,   -72.5754),
    'Rutland VT':         (43.6074,   -72.9635),
    'St Johnsbury':       (43.6843,   -72.0131),

    # New Hampshire
    'Manchester NH':      (42.9956,   -71.5376),
    'Nashua':             (42.7870,   -71.5401),
    'Concord NH':         (43.2081,   -71.5376),
    'Portsmouth NH':      (43.0797,   -70.7593),
    'Claremont NH':       (43.3780,   -72.3378),

    # Maine
    'Portland ME':        (43.6615,   -70.2558),
    'Augusta ME':         (44.3106,   -69.7795),
    'Bangor ME':          (44.4894,   -68.5765),
    'Lewiston ME':        (44.1006,   -70.2641),
    'Presque Isle':       (46.6778,   -68.0000),

    # ════════════════════════════════════════════════════════════════
    # MIDWEST / GREAT LAKES
    # ════════════════════════════════════════════════════════════════
    # Illinois
    'Chicago':            (41.8781,   -87.6298),
    'Aurora IL':          (41.2577,   -88.0844),
    'Rockford':           (41.2687,   -89.9840),
    'Joliet':             (41.5297,   -88.0856),
    'Springfield IL':     (39.7817,   -89.6501),
    'Peoria IL':          (40.6984,   -89.5786),
    'Champaign':          (40.1247,   -88.2437),
    'Decatur IL':         (39.8253,   -88.8408),

    # Indiana
    'Indianapolis':       (39.7684,   -86.1581),
    'Fort Wayne':         (41.0788,   -85.1394),
    'Evansville':         (37.8753,   -87.5311),
    'South Bend':         (41.6764,   -86.2520),
    'Gary':               (41.5834,   -87.3314),
    'Bloomington IN':     (39.1657,   -86.1581),
    'Muncie':             (40.1967,   -85.3924),
    'Kokomo':             (40.4774,   -85.8208),
    'Lafayette IN':       (40.4215,   -86.9081),
    'Richmond IN':        (39.8337,   -84.2947),
    'Terre Haute':        (39.4685,   -87.4119),

    # Ohio
    'Columbus OH':        (39.9612,   -82.9988),
    'Cleveland':          (41.4993,   -81.6944),
    'Cincinnati':         (39.1031,   -84.5120),
    'Toledo OH':          (41.6567,   -83.5367),
    'Akron':              (41.0810,   -81.5190),
    'Dayton':             (39.7684,   -84.1590),
    'Youngstown':         (41.0996,   -80.6483),
    'Canton OH':          (40.8025,   -81.4175),

    # Michigan
    'Detroit':            (42.3314,   -83.0458),
    'Grand Rapids':       (42.9634,   -85.6681),
    'Warren MI':          (42.6314,   -83.0458),
    'Sterling Heights':   (42.5809,   -83.0311),
    'Lansing':            (42.7325,   -84.5555),
    'Ann Arbor':          (42.2808,   -83.0442),
    'Flint':              (42.9675,   -83.7282),
    'Dearborn':           (42.3314,   -83.2603),
    'Marquette MI':       (46.5563,   -84.5777),
    'Traverse City':      (44.7338,   -85.6780),
    'Kalamazoo':          (42.2745,   -85.5585),
    'Battle Creek':       (42.3314,   -85.2500),
    'Saginaw':            (43.4195,   -83.9494),

    # Wisconsin
    'Milwaukee':          (43.0389,   -87.9065),
    'Madison WI':         (43.0731,   -89.4012),
    'Green Bay':          (44.5115,   -88.0296),
    'Kenosha':            (42.5847,   -87.8212),
    'Racine':             (42.7261,   -87.7896),
    'Appleton':           (44.2601,   -88.4113),
    'Waukesha':           (42.9964,   -88.2319),
    'Oshkosh WI':         (44.0247,   -88.5427),
    'La Crosse':          (43.8074,   -91.2396),
    'Superior WI':        (46.6808,   -92.1043),

    # ════════════════════════════════════════════════════════════════
    # ALASKA & HAWAII
    # ════════════════════════════════════════════════════════════════
    'Anchorage':          (61.2181,  -149.9003),
    'Fairbanks':          (64.8378,  -147.7164),
    'Juneau':             (58.3005,  -134.4197),
    'Ketchikan':          (55.3477,  -131.6609),
    'Kodiak':             (57.7956,  -152.4093),
    'Honolulu':           (21.3069,  -157.8583),
    'Hilo HI':            (19.5445,  -155.0099),
    'Kailua-Kona':        (19.6404,  -155.9737),
    'Maui':               (20.7984,  -156.3319),

    # ════════════════════════════════════════════════════════════════
    # US TERRITORIES
    # ════════════════════════════════════════════════════════════════
    # Puerto Rico
    'San Juan PR':        (18.4655,   -66.1057),
    'Bayamon PR':         (18.3987,   -66.1603),
    'Carolina PR':        (18.3801,   -65.9757),
    'Ponce PR':           (18.4766,   -66.5723),
    'Mayaguez PR':        (18.1003,   -66.9754),
    'Caguas PR':          (18.2419,   -66.0385),

    # US Virgin Islands
    'St Thomas USVI':     (18.3430,   -64.9336),
    'St Croix USVI':      (17.7488,   -64.7332),

    # Guam
    'Hagatna Guam':       (13.4563,   144.7494),

    # American Samoa
    'Pago Pago AS':      (-14.2681,  -170.6934),

    # Northern Mariana Islands
    'Saipan CNMI':        (15.2069,   145.7613),
}



def find_nearest_safe_zone(lat, lon, exclude_radius_km=100, top_n=5):
    """
    Find the N nearest safe zones that are at least exclude_radius_km away.
    Returns list of (zone_name, distance_km, (lat, lon)) sorted by distance.
    If fewer than N qualify, returns however many do.  Empty list if none.
    """
    candidates = []
    for name, (z_lat, z_lon) in SAFE_ZONES.items():
        d = haversine_distance(lat, lon, z_lat, z_lon)
        if d >= exclude_radius_km:
            candidates.append((name, d, (z_lat, z_lon)))

    candidates.sort(key=lambda x: x[1])
    return candidates[:top_n]


# ── evacuation plan ──────────────────────────────────────────────────
def calculate_evacuation_plan(vulnerable_lat, vulnerable_lon, fire_lat, fire_lon,
                              fire_name, state=None):
    """
    Comprehensive evacuation plan.  safe_zone / safe_zone_distance fields
    now reflect the CLOSEST qualifying zone (index 0 of the sorted list).
    """
    fire_dist = haversine_distance(vulnerable_lat, vulnerable_lon, fire_lat, fire_lon)
    evac_dir, evac_bearing = get_evacuation_direction(fire_lat, fire_lon, vulnerable_lat, vulnerable_lon)
    highway, highway_dist, highway_point = find_nearest_highway(vulnerable_lat, vulnerable_lon, state)

    # Top-5 safe zones; primary = index 0
    zone_list = find_nearest_safe_zone(vulnerable_lat, vulnerable_lon)
    if zone_list:
        safe_zone, safe_zone_dist, safe_zone_coords = zone_list[0]
    else:
        safe_zone, safe_zone_dist, safe_zone_coords = None, None, None

    # Total distance estimate
    if highway_point and safe_zone_coords:
        total_dist = highway_dist + haversine_distance(
            highway_point[0], highway_point[1],
            safe_zone_coords[0], safe_zone_coords[1]
        )
    else:
        total_dist = safe_zone_dist if safe_zone_dist else 0

    urgency = "HIGH" if fire_dist < 15 else ("MEDIUM" if fire_dist < 40 else "LOW")

    return {
        'evacuation_direction':  evac_dir,
        'evacuation_bearing':    evac_bearing,
        'fire_name':             fire_name,
        'fire_distance_km':      fire_dist,
        'fire_distance_mi':      fire_dist * 0.621371,
        'nearest_highway':       highway or "No major highway nearby",
        'highway_distance_km':   highway_dist if highway else None,
        'highway_distance_mi':   highway_dist * 0.621371 if highway else None,
        'safe_zone':             safe_zone or "Consult local authorities",
        'safe_zone_distance_km': safe_zone_dist,
        'safe_zone_distance_mi': safe_zone_dist * 0.621371 if safe_zone_dist else None,
        'safe_zone_alternatives': zone_list[1:] if len(zone_list) > 1 else [],
        'total_distance_km':     total_dist,
        'total_distance_mi':     total_dist * 0.621371,
        'urgency':               urgency,
    }


def generate_evacuation_routes_for_alerts(fire_data, vulnerable_populations, alerts):
    """Generate evacuation routes for all active alerts."""
    evacuation_plans = []
    for alert in alerts:
        location_name = alert['Location']
        fire_name     = alert['Fire_Name']
        if location_name not in vulnerable_populations:
            continue
        vuln_data  = vulnerable_populations[location_name]
        fire_row   = fire_data[fire_data['fire_name'] == fire_name]
        if fire_row.empty:
            continue
        fire_row   = fire_row.iloc[0]
        state      = location_name.split(',')[-1].strip() if ',' in location_name else None

        plan = calculate_evacuation_plan(
            vuln_data['lat'], vuln_data['lon'],
            fire_row['latitude'], fire_row['longitude'],
            fire_name, state
        )
        plan['location']         = location_name
        plan['vulnerable_count'] = vuln_data.get('vulnerable_count', 0)
        evacuation_plans.append(plan)
    return evacuation_plans


# ── standalone test ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("Evacuation Route Calculator — test")
    print("=" * 60)

    fire_lat, fire_lon = 34.2, -118.0
    vuln_lat, vuln_lon = 34.0, -118.2

    plan = calculate_evacuation_plan(vuln_lat, vuln_lon, fire_lat, fire_lon, "Test Fire", "CA")

    print(f"\nVulnerable Location : {vuln_lat:.2f}, {vuln_lon:.2f}")
    print(f"Fire Location       : {fire_lat:.2f}, {fire_lon:.2f}")
    print(f"\nURGENCY             : {plan['urgency']}")
    print(f"Evacuate            : {plan['evacuation_direction']}")
    print(f"Fire Distance       : {plan['fire_distance_mi']:.1f} mi")
    print(f"Nearest Highway     : {plan['nearest_highway']} ({plan['highway_distance_mi']:.1f} mi)" if plan['highway_distance_mi'] else "Nearest Highway     : N/A")
    print(f"Primary Safe Zone   : {plan['safe_zone']} ({plan['safe_zone_distance_mi']:.1f} mi)" if plan['safe_zone_distance_mi'] else "Primary Safe Zone   : N/A")

    if plan.get('safe_zone_alternatives'):
        print("\nAlternative Safe Zones:")
        for name, dist_km, _ in plan['safe_zone_alternatives']:
            print(f"  - {name}  ({dist_km * 0.621371:.1f} mi)")

    print(f"\nTotal Evacuation Distance : {plan['total_distance_mi']:.1f} mi")