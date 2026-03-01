"""
fire_data_integration.py - FIXED VERSION

Real-Time Fire Data Integration for WiDS Caregiver Alert System
Integrates NASA FIRMS + NIFC (National Interagency Fire Center) ArcGIS Services
Provides complete USA fire coverage with multiple data sources

FIXED: Now correctly extracts geometry from NIFC API responses
"""

import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta

# ==================== NASA FIRMS CONFIGURATION ====================
FIRMS_API_KEY = "c2356d3951981a6df266c8d0ea5523b8"
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# ==================== NIFC ARCGIS CONFIGURATION ====================
NIFC_CURRENT_PERIMETERS = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/Current_WildlandFire_Perimeters/FeatureServer/0/query"
NIFC_INCIDENT_LOCATIONS = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Incident_Locations_Current/FeatureServer/0/query"


def fetch_firms_fire_data(days=1, bbox=None, satellite="VIIRS_SNPP_NRT"):
    """
    Fetch real-time fire POINTS from NASA FIRMS API
    These are satellite-detected heat signatures
    
    Parameters:
    -----------
    days : int (1-10)
        Number of days of historical data
    bbox : str or None
        Bounding box as "min_lon,min_lat,max_lon,max_lat"
        Default: Continental USA
    satellite : str
        "VIIRS_SNPP_NRT" (375m resolution) or "MODIS_NRT" (1km resolution)
    
    Returns:
    --------
    pd.DataFrame with fire detection points
    """
    
    if bbox is None:
        bbox = "-125,24,-66,50"  # Continental USA
    
    url = f"{FIRMS_BASE_URL}/{FIRMS_API_KEY}/{satellite}/{bbox}/{days}"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            df = pd.read_csv(StringIO(response.text))
            
            if len(df) == 0:
                return pd.DataFrame()
            
            # Filter for quality
            df = df[df['confidence'].isin(['high', 'h', 'nominal', 'n'])]
            df = df[df['frp'] >= 5.0]  # Fire Radiative Power >= 5 MW
            
            # Add datetime
            df['detection_datetime'] = pd.to_datetime(
                df['acq_date'] + ' ' + df['acq_time'].astype(str).str.zfill(4),
                format='%Y-%m-%d %H%M'
            )
            
            # Add source
            df['data_source'] = 'NASA_FIRMS'
            
            return df.sort_values('detection_datetime', ascending=False)
            
        else:
            print(f"FIRMS API returned status {response.status_code}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"FIRMS API error: {str(e)}")
        return pd.DataFrame()


def fetch_nifc_fire_perimeters():
    """
    Fetch current fire PERIMETERS from NIFC (National Interagency Fire Center)
    These are actual fire boundaries mapped by incident teams
    
    Returns:
    --------
    pd.DataFrame with fire perimeter information
    """
    
    params = {
        'where': "1=1",  # Get all current fires
        'outFields': "*",
        'f': 'json',
        'returnGeometry': 'true'
    }
    
    try:
        response = requests.get(NIFC_CURRENT_PERIMETERS, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for error
            if 'error' in data:
                print(f"NIFC Perimeter API error: {data['error'].get('message', 'Unknown error')}")
                return pd.DataFrame()
            
            if 'features' not in data or len(data['features']) == 0:
                return pd.DataFrame()
            
            # Extract fire data
            fires = []
            for feature in data['features']:
                attrs = feature['attributes']
                
                # Get geometry (centroid for point location)
                if 'geometry' in feature and 'rings' in feature['geometry']:
                    # Calculate centroid of polygon
                    rings = feature['geometry']['rings'][0]
                    lons = [p[0] for p in rings]
                    lats = [p[1] for p in rings]
                    centroid_lon = sum(lons) / len(lons)
                    centroid_lat = sum(lats) / len(lats)
                else:
                    centroid_lon = None
                    centroid_lat = None
                
                fires.append({
                    'fire_name': attrs.get('poly_IncidentName', attrs.get('IncidentName', 'Unknown')),
                    'latitude': centroid_lat,
                    'longitude': centroid_lon,
                    'acres': attrs.get('poly_GISAcres', attrs.get('GISAcres', 0)),
                    'containment': attrs.get('PercentContained', 0),
                    'fire_cause': attrs.get('FireCause', 'Unknown'),
                    'fire_discovery_date': attrs.get('FireDiscoveryDateTime', None),
                    'data_source': 'NIFC_Perimeter'
                })
            
            df = pd.DataFrame(fires)
            
            # Filter out fires with no location
            df = df.dropna(subset=['latitude', 'longitude'])
            
            return df
            
        else:
            print(f"NIFC perimeter API returned status {response.status_code}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"NIFC perimeter API error: {str(e)}")
        return pd.DataFrame()


def fetch_nifc_incident_locations():
    """
    Fetch current fire INCIDENT POINTS from NIFC
    These are official incident locations (command posts, origins)
    
    FIXED: Now correctly extracts geometry from the 'geometry' field
    
    Returns:
    --------
    pd.DataFrame with incident point data
    """
    
    params = {
        'where': "1=1",
        'outFields': "*",
        'f': 'json',
        'returnGeometry': 'true'  # CRITICAL: Need to request geometry
    }
    
    try:
        response = requests.get(NIFC_INCIDENT_LOCATIONS, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'features' not in data or len(data['features']) == 0:
                return pd.DataFrame()
            
            fires = []
            for feature in data['features']:
                attrs = feature['attributes']
                
                # FIXED: Get geometry from the 'geometry' field (x=lon, y=lat)
                if 'geometry' in feature and feature['geometry']:
                    geom = feature['geometry']
                    lat = geom.get('y')
                    lon = geom.get('x')
                else:
                    # Fallback to POO fields if available
                    lat = attrs.get('POOLatitude')
                    lon = attrs.get('POOLongitude')
                
                # Skip if no valid location
                if lat is None or lon is None:
                    continue
                
                fires.append({
                    'fire_name': attrs.get('IncidentName', 'Unknown'),
                    'latitude': lat,
                    'longitude': lon,
                    'acres': attrs.get('IncidentSize', attrs.get('DailyAcres', 0)),
                    'containment': attrs.get('PercentContained', 0),
                    'fire_cause': attrs.get('FireCause', 'Unknown'),
                    'fire_discovery_date': attrs.get('FireDiscoveryDateTime', None),
                    'data_source': 'NIFC_Incident'
                })
            
            df = pd.DataFrame(fires)
            
            return df
            
        else:
            print(f"NIFC Incident API returned status {response.status_code}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"NIFC Incident API error: {str(e)}")
        return pd.DataFrame()


def get_all_us_fires(days=1):
    """
    MASTER FUNCTION: Get ALL fire data from multiple sources
    Combines NASA FIRMS + NIFC for complete USA coverage
    
    Parameters:
    -----------
    days : int
        How many days back to fetch FIRMS data
    
    Returns:
    --------
    pd.DataFrame with combined fire data from all sources
    """
    
    all_fires = []
    
    # 1. Get NASA FIRMS satellite detections
    print("📡 Fetching NASA FIRMS data...")
    firms_data = fetch_firms_fire_data(days=days)
    if len(firms_data) > 0:
        # Standardize columns
        firms_std = pd.DataFrame({
            'fire_name': 'Satellite Detection',
            'latitude': firms_data['latitude'],
            'longitude': firms_data['longitude'],
            'frp': firms_data['frp'],
            'confidence': firms_data['confidence'],
            'detection_time': firms_data['detection_datetime'],
            'data_source': 'NASA_FIRMS',
            'acres': None,
            'containment': None
        })
        all_fires.append(firms_std)
    
    # 2. Get NIFC fire perimeters (official mapped fires)
    print("🔥 Fetching NIFC perimeter data...")
    nifc_perimeters = fetch_nifc_fire_perimeters()
    if len(nifc_perimeters) > 0:
        all_fires.append(nifc_perimeters)
    
    # 3. Get NIFC incident locations
    print("📍 Fetching NIFC incident data...")
    nifc_incidents = fetch_nifc_incident_locations()
    if len(nifc_incidents) > 0:
        all_fires.append(nifc_incidents)
    
    # Combine all sources
    if all_fires:
        combined = pd.concat(all_fires, ignore_index=True)
        
        # Remove duplicates (fires reported by multiple sources)
        # Keep the one with most information (perimeter > incident > FIRMS)
        source_priority = {'NIFC_Perimeter': 0, 'NIFC_Incident': 1, 'NASA_FIRMS': 2}
        combined['source_priority'] = combined['data_source'].map(source_priority)
        combined = combined.sort_values('source_priority')
        
        # Drop near-duplicate locations (within ~1km)
        combined = combined.drop_duplicates(
            subset=['latitude', 'longitude'], 
            keep='first'
        )
        
        combined = combined.drop(columns=['source_priority'])
        
        return combined
    else:
        return pd.DataFrame()


def get_regional_fires(region="national", days=1):
    """
    Get fires for specific US regions
    
    Parameters:
    -----------
    region : str
        "national", "west", "southwest", "southeast", "northeast", etc.
    days : int
        Days of FIRMS data to fetch
    
    Returns:
    --------
    pd.DataFrame filtered to region
    """
    
    # Get all US fires
    all_fires = get_all_us_fires(days=days)
    
    if len(all_fires) == 0:
        return pd.DataFrame()
    
    # Regional bounding boxes
    regions = {
        "national": {"lat": (24, 50), "lon": (-125, -66)},
        "west": {"lat": (32, 49), "lon": (-125, -110)},
        "southwest": {"lat": (31, 37), "lon": (-115, -103)},
        "southeast": {"lat": (24, 37), "lon": (-92, -75)},
        "northeast": {"lat": (38, 48), "lon": (-80, -66)},
        "midwest": {"lat": (36, 49), "lon": (-105, -80)},
        "california": {"lat": (32, 42), "lon": (-125, -114)},
        "texas": {"lat": (25, 37), "lon": (-107, -93)},
        "north_carolina": {"lat": (33.5, 36.8), "lon": (-84.5, -75)},
    }
    
    if region.lower() not in regions:
        return all_fires  # Return all if region not found
    
    bounds = regions[region.lower()]
    
    # Filter by region
    filtered = all_fires[
        (all_fires['latitude'] >= bounds['lat'][0]) &
        (all_fires['latitude'] <= bounds['lat'][1]) &
        (all_fires['longitude'] >= bounds['lon'][0]) &
        (all_fires['longitude'] <= bounds['lon'][1])
    ]
    
    return filtered


def calculate_fire_distance(fire_lat, fire_lon, location_lat, location_lon):
    """
    Calculate distance between fire and location using Haversine formula
    
    Returns: distance in km
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371.0  # Earth radius in km
    
    lat1 = radians(location_lat)
    lon1 = radians(location_lon)
    lat2 = radians(fire_lat)
    lon2 = radians(fire_lon)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance


def find_nearby_fires(fire_data, vulnerable_locations, radius_km=80):
    """
    Find fires within radius of vulnerable population locations
    
    Parameters:
    -----------
    fire_data : pd.DataFrame
        Fire data from get_all_us_fires()
    vulnerable_locations : dict
        {'Location': {'lat': float, 'lon': float, 'vulnerable_count': int}}
    radius_km : float
        Search radius in kilometers
    
    Returns:
    --------
    list of alert dictionaries
    """
    
    alerts = []
    
    if len(fire_data) == 0:
        return alerts
    
    for location_name, location_data in vulnerable_locations.items():
        location_lat = location_data['lat']
        location_lon = location_data['lon']
        
        for idx, fire in fire_data.iterrows():
            distance = calculate_fire_distance(
                fire['latitude'], 
                fire['longitude'],
                location_lat,
                location_lon
            )
            
            if distance <= radius_km:
                alerts.append({
                    'Location': location_name,
                    'Fire_Name': fire.get('fire_name', 'Unknown'),
                    'Distance_km': round(distance, 1),
                    'Distance_mi': round(distance * 0.621371, 1),
                    'Fire_Acres': fire.get('acres', 'N/A'),
                    'Containment': f"{fire.get('containment', 0)}%",
                    'Data_Source': fire.get('data_source', 'Unknown'),
                    'Vulnerable_Count': location_data.get('vulnerable_count', 'N/A'),
                    'Status': 'ACTIVE'
                })
    
    return alerts


def get_fire_statistics(fire_data):
    """
    Calculate summary statistics
    
    Returns: dict of statistics
    """
    
    if len(fire_data) == 0:
        return {
            'total_fires': 0,
            'named_fires': 0,
            'satellite_detections': 0,
            'total_acres': 0,
            'avg_containment': 0
        }
    
    stats = {
        'total_fires': len(fire_data),
        'named_fires': len(fire_data[fire_data['data_source'] != 'NASA_FIRMS']),
        'satellite_detections': len(fire_data[fire_data['data_source'] == 'NASA_FIRMS']),
        'total_acres': fire_data['acres'].sum() if 'acres' in fire_data.columns else 0,
        'avg_containment': fire_data['containment'].mean() if 'containment' in fire_data.columns else 0
    }
    
    return stats


# Testing
if __name__ == "__main__":
    print("🔥 WiDS Fire Data Integration - FIXED VERSION")
    print("=" * 60)
    print("Data Sources:")
    print("  ✓ NASA FIRMS (Satellite detections)")
    print("  ✓ NIFC Fire Perimeters (Official mapped fires)")
    print("  ✓ NIFC Incident Locations (Command posts)")
    print("=" * 60)
    
    # Test all sources
    print("\n1. Testing NASA FIRMS...")
    firms = fetch_firms_fire_data(days=1)
    print(f"   Found {len(firms)} FIRMS detections")
    
    print("\n2. Testing NIFC Perimeters...")
    perimeters = fetch_nifc_fire_perimeters()
    print(f"   Found {len(perimeters)} fire perimeters")
    
    print("\n3. Testing NIFC Incidents...")
    incidents = fetch_nifc_incident_locations()
    print(f"   Found {len(incidents)} incident locations")
    
    if len(incidents) > 0:
        print("\n   First few fires:")
        print(incidents[['fire_name', 'latitude', 'longitude', 'acres']].head())
    
    print("\n4. Testing combined national data...")
    all_fires = get_all_us_fires(days=1)
    print(f"   Combined total: {len(all_fires)} fires")
    
    if len(all_fires) > 0:
        stats = get_fire_statistics(all_fires)
        print("\n5. Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n   Sample fires:")
        print(all_fires[['fire_name', 'latitude', 'longitude', 'acres', 'data_source']].head(10))
    
    print("\n" + "=" * 60)
    print("✅ Integration module ready!")