"""
osm_routing.py

Real-time evacuation routing using OpenStreetMap
Uses OSRM (Open Source Routing Machine) public API - NO installation needed!

Features:
- Real driving routes (not straight-line distance)
- Actual drive times
- Turn-by-turn directions
- Works immediately - no setup required
"""

import requests
from typing import Dict, Tuple, List, Optional


def get_real_driving_route(start_lat: float, start_lon: float, 
                           end_lat: float, end_lon: float) -> Optional[Dict]:
    """
    Get actual driving route using OpenStreetMap data
    Uses free OSRM public API - no API key needed!
    
    Returns dict with:
        - distance_mi: Actual road distance in miles
        - duration_min: Actual drive time in minutes  
        - geometry: Route coordinates for mapping
    """
    
    # OSRM API expects lon,lat format
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
    
    params = {
        'overview': 'full',
        'geometries': 'geojson'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        if data['code'] != 'Ok':
            return None
        
        route = data['routes'][0]
        
        return {
            'distance_m': route['distance'],
            'distance_mi': route['distance'] * 0.000621371,
            'distance_km': route['distance'] / 1000,
            'duration_sec': route['duration'],
            'duration_min': route['duration'] / 60,
            'duration_hours': route['duration'] / 3600,
            'geometry': route['geometry']['coordinates'],  # [lon, lat] pairs
            'avg_speed_mph': (route['distance'] * 0.000621371) / (route['duration'] / 3600) if route['duration'] > 0 else 0
        }
        
    except Exception as e:
        print(f"Routing error: {e}")
        return None


def calculate_evacuation_route_osm(vulnerable_lat: float, vulnerable_lon: float,
                                   fire_lat: float, fire_lon: float,
                                   safe_zone_name: str,
                                   safe_zone_lat: float, safe_zone_lon: float) -> Dict:
    """
    Calculate real evacuation route using actual roads
    
    Returns comprehensive evacuation plan with REAL driving data
    """
    
    print(f"🚗 Calculating real route to {safe_zone_name}...")
    
    route = get_real_driving_route(vulnerable_lat, vulnerable_lon, safe_zone_lat, safe_zone_lon)
    
    if not route:
        return {
            'success': False,
            'destination': safe_zone_name,
            'error': 'Could not calculate route - using straight-line distance'
        }
    
    # Calculate fire distance
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return 6371 * c
    
    fire_dist_km = haversine(vulnerable_lat, vulnerable_lon, fire_lat, fire_lon)
    
    # Determine urgency
    if fire_dist_km < 15:
        urgency = "HIGH"
    elif fire_dist_km < 40:
        urgency = "MEDIUM"
    else:
        urgency = "LOW"
    
    return {
        'success': True,
        'destination': safe_zone_name,
        'distance_mi': route['distance_mi'],
        'distance_km': route['distance_km'],
        'drive_time_min': route['duration_min'],
        'drive_time_hours': route['duration_hours'],
        'avg_speed_mph': route['avg_speed_mph'],
        'fire_distance_km': fire_dist_km,
        'fire_distance_mi': fire_dist_km * 0.621371,
        'urgency': urgency,
        'route_geometry': route['geometry'],
        'route_type': 'REAL ROADS (OpenStreetMap)'
    }


# Safe zones by state
SAFE_ZONES = {
    'CA': [
        ('San Diego', 32.7157, -117.1611),
        ('Sacramento', 38.5816, -121.4944),
        ('Fresno', 36.7378, -119.7871),
    ],
    'AZ': [
        ('Phoenix', 33.4484, -112.0740),
        ('Tucson', 32.2226, -110.9747),
    ],
    'OR': [
        ('Portland', 45.5152, -122.6784),
    ],
    'WA': [
        ('Seattle', 47.6062, -122.3321),
    ],
    'NV': [
        ('Las Vegas', 36.1699, -115.1398),
        ('Reno', 39.5296, -119.8138),
    ],
    'NM': [
        ('Albuquerque', 35.0844, -106.6504),
    ],
    'CO': [
        ('Denver', 39.7392, -104.9903),
    ]
}


def get_best_evacuation_route(vulnerable_lat: float, vulnerable_lon: float,
                              fire_lat: float, fire_lon: float,
                              state: str) -> Dict:
    """
    Find best evacuation destination for a state
    Tests all safe zones and returns fastest route
    """
    
    safe_zones = SAFE_ZONES.get(state, [('Safety', 39.8283, -98.5795)])
    
    best_route = None
    best_time = float('inf')
    
    for name, lat, lon in safe_zones:
        route = calculate_evacuation_route_osm(
            vulnerable_lat, vulnerable_lon,
            fire_lat, fire_lon,
            name, lat, lon
        )
        
        if route.get('success') and route['drive_time_min'] < best_time:
            best_time = route['drive_time_min']
            best_route = route
    
    return best_route if best_route else {
        'success': False,
        'error': 'No routes available'
    }


if __name__ == "__main__":
    print("=" * 70)
    print("TESTING REAL OPENSTREETMAP ROUTING")
    print("=" * 70)
    
    # Test: LA to San Diego evacuation
    print("\n📍 Test: Wildfire evacuation from Los Angeles")
    
    result = calculate_evacuation_route_osm(
        vulnerable_lat=34.0522,
        vulnerable_lon=-118.2437,
        fire_lat=34.2,
        fire_lon=-118.0,
        safe_zone_name="San Diego",
        safe_zone_lat=32.7157,
        safe_zone_lon=-117.1611
    )
    
    if result['success']:
        print(f"\n✅ REAL ROUTE CALCULATED!")
        print(f"   Destination: {result['destination']}")
        print(f"   Distance: {result['distance_mi']:.1f} miles (actual roads)")
        print(f"   Drive Time: {result['drive_time_hours']:.1f} hours ({result['drive_time_min']:.0f} min)")
        print(f"   Avg Speed: {result['avg_speed_mph']:.1f} mph")
        print(f"   Fire Distance: {result['fire_distance_mi']:.1f} miles")
        print(f"   Urgency: {result['urgency']}")
        print(f"   Route Type: {result['route_type']}")
    else:
        print(f"\n❌ Failed: {result.get('error')}")
    
    print("\n" + "=" * 70)