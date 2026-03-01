"""
us_territories_data.py

Complete geographic and emergency data for U.S. territories:
- Puerto Rico
- U.S. Virgin Islands (St. Thomas, St. Croix, St. John)
- Guam
- American Samoa
- Northern Mariana Islands (Saipan, Tinian, Rota)

Includes: Safe zones, emergency contacts, vulnerable populations,
          major highways, airports, hospitals

Author: 49ers Intelligence Lab  
Date: 2025-02-11
"""

from typing import Dict, List, Tuple


# ══════════════════════════════════════════════════════════════════════
# PUERTO RICO
# ══════════════════════════════════════════════════════════════════════

PUERTO_RICO_SAFE_ZONES = {
    # Major cities (evacuate inland during hurricanes/fires)
    'San Juan':         (18.4655, -66.1057),
    'Bayamón':          (18.3987, -66.1603),
    'Carolina':         (18.3801, -65.9757),
    'Ponce':            (18.0111, -66.6141),
    'Caguas':           (18.2419, -66.0385),
    'Mayagüez':         (18.2011, -67.1397),
    'Guaynabo':         (18.3557, -66.1088),
    'Trujillo Alto':    (18.3475, -66.0074),
    'Arecibo':          (18.4727, -66.7149),
    'Aguadilla':        (18.4278, -67.1540),
    'Fajardo':          (18.3258, -65.6525),
    'Humacao':          (18.1497, -65.8272),
    
    # Interior (safer from coastal fires)
    'Ciales':           (18.3360, -66.4686),
    'Utuado':           (18.2656, -66.7004),
    'Adjuntas':         (18.1629, -66.7221),
    'Jayuya':           (18.2185, -66.5915),
}

PUERTO_RICO_EMERGENCY = {
    'fire_911': '911',
    'police_911': '911',
    'ambulance': '911',
    'emergency_management': '787-724-0124',
    'red_cross_pr': '787-758-8150',
    'fema_pr': '800-621-3362',
    'highway_patrol': '787-793-1234',
    'coastal_guard': '787-289-2041',
}

PUERTO_RICO_HOSPITALS = [
    ('Hospital Auxilio Mutuo', 18.4269, -66.0696),
    ('San Jorge Children\'s Hospital', 18.4172, -66.0642),
    ('Hospital UPR Carolina', 18.3963, -65.9654),
    ('Hospital Menonita Cayey', 18.1118, -66.1659),
    ('Hospital San Lucas Ponce', 18.0044, -66.6137),
]

PUERTO_RICO_HIGHWAYS = {
    'PR-52': 'San Juan - Ponce (Autopista Luis A. Ferré)',
    'PR-22': 'San Juan - Arecibo (Autopista de Diego)',
    'PR-53': 'Fajardo - Salinas (Autopista José Luis Feliciano)',
    'PR-66': 'Río Piedras - Caguas',
    'PR-1': 'Coastal Road (North)',
    'PR-2': 'Coastal Road (West/South)',
}


# ══════════════════════════════════════════════════════════════════════
# U.S. VIRGIN ISLANDS
# ══════════════════════════════════════════════════════════════════════

USVI_SAFE_ZONES = {
    # St. Thomas
    'Charlotte Amalie':    (18.3419, -64.9307),
    'Red Hook':            (18.3220, -64.8696),
    'Frenchtown':          (18.3387, -64.9553),
    
    # St. Croix
    'Christiansted':       (17.7477, -64.7036),
    'Frederiksted':        (17.7120, -64.8835),
    
    # St. John
    'Cruz Bay':            (18.3323, -64.7954),
}

USVI_EMERGENCY = {
    'fire_911': '911',
    'police_911': '911',
    'ambulance': '911',
    'vitema': '340-774-2244',  # Virgin Islands Territorial Emergency Management Agency
    'coast_guard': '787-289-2041',
    'hospital_st_thomas': '340-776-8311',
    'hospital_st_croix': '340-778-6311',
}

USVI_HOSPITALS = [
    ('Schneider Regional Medical Center', 18.3356, -64.9421),  # St. Thomas
    ('Governor Juan F. Luis Hospital', 17.7181, -64.7457),      # St. Croix
]


# ══════════════════════════════════════════════════════════════════════
# GUAM
# ══════════════════════════════════════════════════════════════════════

GUAM_SAFE_ZONES = {
    'Hagåtña':        (13.4754, 144.7500),  # Capital
    'Tamuning':       (13.4894, 144.7805),  # Tourist area
    'Dededo':         (13.5158, 144.8369),  # Largest village
    'Mangilao':       (13.4466, 144.8033),
    'Yigo':           (13.5361, 144.8897),
    'Barrigada':      (13.4708, 144.8069),
    'Agana Heights':  (13.4701, 144.7436),
}

GUAM_EMERGENCY = {
    'fire_911': '911',
    'police_911': '911',
    'ambulance': '911',
    'ghs_ocd': '671-475-9600',  # Guam Homeland Security/Office of Civil Defense
    'coast_guard': '671-355-4824',
    'hospital': '671-647-2330',  # Guam Memorial Hospital
}

GUAM_HOSPITALS = [
    ('Guam Memorial Hospital', 13.4445, 144.7937),
    ('Naval Hospital Guam', 13.4474, 144.6486),
    ('Guam Regional Medical City', 13.5158, 144.8369),
]

GUAM_HIGHWAYS = {
    'Route 1': 'Marine Corps Drive (North)',
    'Route 2': 'Army Drive / Route 15 (Central)',
    'Route 4': 'Chalan San Antonio (South)',
}


# ══════════════════════════════════════════════════════════════════════
# AMERICAN SAMOA
# ══════════════════════════════════════════════════════════════════════

AMERICAN_SAMOA_SAFE_ZONES = {
    # Tutuila Island
    'Pago Pago':      (-14.2756, -170.7019),  # Capital
    'Fagatogo':       (-14.2793, -170.6910),
    'Tafuna':         (-14.3317, -170.7281),
    'Utulei':         (-14.2819, -170.6870),
    
    # Manu\'a Islands
    'Ta\'ū':          (-14.2325, -169.5154),
    'Ofu':            (-14.1833, -169.6667),
}

AMERICAN_SAMOA_EMERGENCY = {
    'fire_911': '911',
    'police_911': '911',
    'ambulance': '911',
    'territorial_emergency': '684-699-6415',
    'hospital': '684-633-1222',  # LBJ Tropical Medical Center
}

AMERICAN_SAMOA_HOSPITALS = [
    ('LBJ Tropical Medical Center', -14.2778, -170.6919),
]


# ══════════════════════════════════════════════════════════════════════
# NORTHERN MARIANA ISLANDS
# ══════════════════════════════════════════════════════════════════════

CNMI_SAFE_ZONES = {
    # Saipan (main island)
    'Garapan':        (15.2123, 145.7197),
    'Susupe':         (15.1658, 145.7072),
    'San Vicente':    (15.2097, 145.7614),
    'Kagman':         (15.1897, 145.7869),
    
    # Tinian
    'San Jose':       (14.9508, 145.6181),
    
    # Rota
    'Songsong':       (14.1433, 145.1914),
}

CNMI_EMERGENCY = {
    'fire_911': '911',
    'police_911': '911',
    'ambulance': '911',
    'emergency_management': '670-322-9529',
    'hospital_saipan': '670-236-8201',
}

CNMI_HOSPITALS = [
    ('Commonwealth Health Center', 15.1800, 145.7200),  # Saipan
]


# ══════════════════════════════════════════════════════════════════════
# COMBINED TERRITORIES DATA
# ══════════════════════════════════════════════════════════════════════

ALL_TERRITORIES_SAFE_ZONES = {
    **PUERTO_RICO_SAFE_ZONES,
    **USVI_SAFE_ZONES,
    **GUAM_SAFE_ZONES,
    **AMERICAN_SAMOA_SAFE_ZONES,
    **CNMI_SAFE_ZONES,
}

TERRITORY_EMERGENCY_CONTACTS = {
    'Puerto Rico': PUERTO_RICO_EMERGENCY,
    'U.S. Virgin Islands': USVI_EMERGENCY,
    'Guam': GUAM_EMERGENCY,
    'American Samoa': AMERICAN_SAMOA_EMERGENCY,
    'Northern Mariana Islands': CNMI_EMERGENCY,
}

TERRITORY_HOSPITALS = {
    'Puerto Rico': PUERTO_RICO_HOSPITALS,
    'U.S. Virgin Islands': USVI_HOSPITALS,
    'Guam': GUAM_HOSPITALS,
    'American Samoa': AMERICAN_SAMOA_HOSPITALS,
    'Northern Mariana Islands': CNMI_HOSPITALS,
}


def get_territory_from_coords(lat: float, lon: float) -> str:
    """Determine which territory based on coordinates"""
    
    # Bounding boxes for each territory
    bounds = {
        'Puerto Rico':            {'lat': (17.9, 18.5), 'lon': (-67.3, -65.2)},
        'U.S. Virgin Islands':    {'lat': (17.6, 18.4), 'lon': (-65.1, -64.5)},
        'Guam':                   {'lat': (13.2, 13.7), 'lon': (144.6, 145.0)},
        'American Samoa':         {'lat': (-14.6, -14.0), 'lon': (-171.0, -169.0)},
        'Northern Mariana Islands': {'lat': (14.0, 20.6), 'lon': (144.8, 146.1)},
    }
    
    for territory, box in bounds.items():
        if (box['lat'][0] <= lat <= box['lat'][1] and 
            box['lon'][0] <= lon <= box['lon'][1]):
            return territory
    
    return 'Unknown'


def get_nearest_safe_zone_territory(lat: float, lon: float, territory: str = None) -> Tuple[str, float, Tuple[float, float]]:
    """Find nearest safe zone within a territory"""
    from math import radians, sin, cos, sqrt, atan2
    
    if territory is None:
        territory = get_territory_from_coords(lat, lon)
    
    # Get safe zones for this territory
    if territory == 'Puerto Rico':
        zones = PUERTO_RICO_SAFE_ZONES
    elif territory == 'U.S. Virgin Islands':
        zones = USVI_SAFE_ZONES
    elif territory == 'Guam':
        zones = GUAM_SAFE_ZONES
    elif territory == 'American Samoa':
        zones = AMERICAN_SAMOA_SAFE_ZONES
    elif territory == 'Northern Mariana Islands':
        zones = CNMI_SAFE_ZONES
    else:
        return None, None, None
    
    # Haversine distance
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # km
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        return R * 2 * atan2(sqrt(a), sqrt(1-a))
    
    min_dist = float('inf')
    nearest = None
    nearest_coords = None
    
    for name, (z_lat, z_lon) in zones.items():
        dist = haversine(lat, lon, z_lat, z_lon)
        if dist < min_dist:
            min_dist = dist
            nearest = name
            nearest_coords = (z_lat, z_lon)
    
    return nearest, min_dist, nearest_coords


def get_territory_emergency_contacts(territory: str) -> Dict[str, str]:
    """Get emergency contact numbers for a territory"""
    return TERRITORY_EMERGENCY_CONTACTS.get(territory, {})


def get_territory_hospitals(territory: str) -> List[Tuple[str, float, float]]:
    """Get hospital locations for a territory"""
    return TERRITORY_HOSPITALS.get(territory, [])


# Vulnerability data (CDC SVI-style) for territories
TERRITORY_VULNERABLE_POPULATIONS = {
    # Puerto Rico (post-Hurricane Maria, high vulnerability)
    'San Juan, PR':         {'lat': 18.4655, 'lon': -66.1057, 'vulnerable_count': 892, 'svi_score': 0.89},
    'Ponce, PR':            {'lat': 18.0111, 'lon': -66.6141, 'vulnerable_count': 456, 'svi_score': 0.92},
    'Caguas, PR':           {'lat': 18.2419, 'lon': -66.0385, 'vulnerable_count': 378, 'svi_score': 0.87},
    
    # U.S. Virgin Islands
    'St. Thomas, USVI':     {'lat': 18.3419, 'lon': -64.9307, 'vulnerable_count': 234, 'svi_score': 0.85},
    'St. Croix, USVI':      {'lat': 17.7477, 'lon': -64.7036, 'vulnerable_count': 198, 'svi_score': 0.88},
    
    # Guam
    'Hagåtña, Guam':        {'lat': 13.4754, 'lon': 144.7500, 'vulnerable_count': 156, 'svi_score': 0.76},
    'Dededo, Guam':         {'lat': 13.5158, 'lon': 144.8369, 'vulnerable_count': 189, 'svi_score': 0.79},
    
    # American Samoa
    'Pago Pago, AS':        {'lat': -14.2756, 'lon': -170.7019, 'vulnerable_count': 98, 'svi_score': 0.82},
    
    # Northern Mariana Islands
    'Saipan, CNMI':         {'lat': 15.2123, 'lon': 145.7197, 'vulnerable_count': 112, 'svi_score': 0.80},
}


if __name__ == "__main__":
    print("🌴 U.S. Territories Emergency Data")
    print("=" * 60)
    
    print(f"\nTotal Safe Zones: {len(ALL_TERRITORIES_SAFE_ZONES)}")
    print(f"Territories Covered: {len(TERRITORY_EMERGENCY_CONTACTS)}")
    
    # Test coordinate detection
    test_coords = [
        (18.4655, -66.1057, "San Juan, PR"),
        (18.3419, -64.9307, "St. Thomas, USVI"),
        (13.4754, 144.7500, "Hagåtña, Guam"),
        (-14.2756, -170.7019, "Pago Pago, AS"),
        (15.2123, 145.7197, "Saipan, CNMI"),
    ]
    
    print("\nTerritory Detection Tests:")
    for lat, lon, location in test_coords:
        territory = get_territory_from_coords(lat, lon)
        print(f"  {location}: {territory}")
    
    # Test safe zone finder
    print("\nNearest Safe Zone Tests:")
    for lat, lon, location in test_coords:
        nearest, dist, coords = get_nearest_safe_zone_territory(lat, lon)
        print(f"  {location} → {nearest} ({dist:.1f} km)")
    
    print("\n✅ Module ready for integration")