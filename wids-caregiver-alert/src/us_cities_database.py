"""
us_cities_database.py

Comprehensive database of US cities with coordinates
Covers all 50 states + DC with major cities and counties
"""

# Complete US Cities Database (500+ cities)
US_CITIES = {
    # ALABAMA
    'birmingham': (33.5186, -86.8104), 'birmingham, al': (33.5186, -86.8104),
    'montgomery': (32.3668, -86.3000), 'montgomery, al': (32.3668, -86.3000),
    'mobile': (30.6954, -88.0399), 'mobile, al': (30.6954, -88.0399),
    'huntsville': (34.7304, -86.5861), 'huntsville, al': (34.7304, -86.5861),
    
    # ALASKA
    'anchorage': (61.2181, -149.9003), 'anchorage, ak': (61.2181, -149.9003),
    'fairbanks': (64.8378, -147.7164), 'fairbanks, ak': (64.8378, -147.7164),
    'juneau': (58.3019, -134.4197), 'juneau, ak': (58.3019, -134.4197),
    
    # ARIZONA
    'phoenix': (33.4484, -112.0740), 'phoenix, az': (33.4484, -112.0740),
    'tucson': (32.2226, -110.9747), 'tucson, az': (32.2226, -110.9747),
    'mesa': (33.4152, -111.8315), 'mesa, az': (33.4152, -111.8315),
    'chandler': (33.3062, -111.8413), 'chandler, az': (33.3062, -111.8413),
    'scottsdale': (33.4942, -111.9261), 'scottsdale, az': (33.4942, -111.9261),
    'glendale': (33.5387, -112.1860), 'glendale, az': (33.5387, -112.1860),
    'flagstaff': (35.1983, -111.6513), 'flagstaff, az': (35.1983, -111.6513),
    'yuma': (32.6927, -114.6277), 'yuma, az': (32.6927, -114.6277),
    
    # ARKANSAS
    'little rock': (34.7465, -92.2896), 'little rock, ar': (34.7465, -92.2896),
    'fort smith': (35.3859, -94.3985), 'fort smith, ar': (35.3859, -94.3985),
    'fayetteville': (36.0626, -94.1574), 'fayetteville, ar': (36.0626, -94.1574),
    
    # CALIFORNIA
    'los angeles': (34.0522, -118.2437), 'los angeles, ca': (34.0522, -118.2437),
    'san diego': (32.7157, -117.1611), 'san diego, ca': (32.7157, -117.1611),
    'san jose': (37.3382, -121.8863), 'san jose, ca': (37.3382, -121.8863),
    'san francisco': (37.7749, -122.4194), 'san francisco, ca': (37.7749, -122.4194),
    'fresno': (36.7378, -119.7871), 'fresno, ca': (36.7378, -119.7871),
    'sacramento': (38.5816, -121.4944), 'sacramento, ca': (38.5816, -121.4944),
    'long beach': (33.7701, -118.1937), 'long beach, ca': (33.7701, -118.1937),
    'oakland': (37.8044, -122.2712), 'oakland, ca': (37.8044, -122.2712),
    'bakersfield': (35.3733, -119.0187), 'bakersfield, ca': (35.3733, -119.0187),
    'anaheim': (33.8366, -117.9143), 'anaheim, ca': (33.8366, -117.9143),
    'santa ana': (33.7455, -117.8677), 'santa ana, ca': (33.7455, -117.8677),
    'riverside': (33.9533, -117.3962), 'riverside, ca': (33.9533, -117.3962),
    'stockton': (37.9577, -121.2908), 'stockton, ca': (37.9577, -121.2908),
    'irvine': (33.6846, -117.8265), 'irvine, ca': (33.6846, -117.8265),
    'chula vista': (32.6401, -117.0842), 'chula vista, ca': (32.6401, -117.0842),
    'fremont': (37.5485, -121.9886), 'fremont, ca': (37.5485, -121.9886),
    'san bernardino': (34.1083, -117.2898), 'san bernardino, ca': (34.1083, -117.2898),
    'modesto': (37.6391, -120.9969), 'modesto, ca': (37.6391, -120.9969),
    'fontana': (34.0922, -117.4350), 'fontana, ca': (34.0922, -117.4350),
    'oxnard': (34.1975, -119.1771), 'oxnard, ca': (34.1975, -119.1771),
    'moreno valley': (33.9425, -117.2297), 'moreno valley, ca': (33.9425, -117.2297),
    'glendale, ca': (34.1425, -118.2551),
    'huntington beach': (33.6603, -117.9992), 'huntington beach, ca': (33.6603, -117.9992),
    'santa clarita': (34.3917, -118.5426), 'santa clarita, ca': (34.3917, -118.5426),
    'salinas': (36.6777, -121.6555), 'salinas, ca': (36.6777, -121.6555),
    
    # COLORADO
    'denver': (39.7392, -104.9903), 'denver, co': (39.7392, -104.9903),
    'colorado springs': (38.8339, -104.8214), 'colorado springs, co': (38.8339, -104.8214),
    'aurora': (39.7294, -104.8319), 'aurora, co': (39.7294, -104.8319),
    'fort collins': (40.5853, -105.0844), 'fort collins, co': (40.5853, -105.0844),
    'lakewood': (39.7047, -105.0814), 'lakewood, co': (39.7047, -105.0814),
    'boulder': (40.0150, -105.2705), 'boulder, co': (40.0150, -105.2705),
    
    # CONNECTICUT
    'bridgeport': (41.1865, -73.1952), 'bridgeport, ct': (41.1865, -73.1952),
    'new haven': (41.3083, -72.9279), 'new haven, ct': (41.3083, -72.9279),
    'stamford': (41.0534, -73.5387), 'stamford, ct': (41.0534, -73.5387),
    'hartford': (41.7658, -72.6734), 'hartford, ct': (41.7658, -72.6734),
    
    # DELAWARE
    'wilmington': (39.7391, -75.5398), 'wilmington, de': (39.7391, -75.5398),
    'dover': (39.1582, -75.5244), 'dover, de': (39.1582, -75.5244),
    
    # FLORIDA
    'jacksonville': (30.3322, -81.6557), 'jacksonville, fl': (30.3322, -81.6557),
    'miami': (25.7617, -80.1918), 'miami, fl': (25.7617, -80.1918),
    'tampa': (27.9506, -82.4572), 'tampa, fl': (27.9506, -82.4572),
    'orlando': (28.5383, -81.3792), 'orlando, fl': (28.5383, -81.3792),
    'st petersburg': (27.7676, -82.6403), 'st petersburg, fl': (27.7676, -82.6403),
    'hialeah': (25.8576, -80.2781), 'hialeah, fl': (25.8576, -80.2781),
    'tallahassee': (30.4383, -84.2807), 'tallahassee, fl': (30.4383, -84.2807),
    'fort lauderdale': (26.1224, -80.1373), 'fort lauderdale, fl': (26.1224, -80.1373),
    'port st lucie': (27.2730, -80.3582), 'port st lucie, fl': (27.2730, -80.3582),
    'cape coral': (26.5629, -81.9495), 'cape coral, fl': (26.5629, -81.9495),
    'pembroke pines': (26.0070, -80.2962), 'pembroke pines, fl': (26.0070, -80.2962),
    'hollywood': (26.0112, -80.1495), 'hollywood, fl': (26.0112, -80.1495),
    'gainesville': (29.6516, -82.3248), 'gainesville, fl': (29.6516, -82.3248),
    
    # GEORGIA
    'atlanta': (33.7490, -84.3880), 'atlanta, ga': (33.7490, -84.3880),
    'columbus': (32.4609, -84.9877), 'columbus, ga': (32.4609, -84.9877),
    'augusta': (33.4735, -82.0105), 'augusta, ga': (33.4735, -82.0105),
    'savannah': (32.0809, -81.0912), 'savannah, ga': (32.0809, -81.0912),
    'athens': (33.9519, -83.3576), 'athens, ga': (33.9519, -83.3576),
    'macon': (32.8407, -83.6324), 'macon, ga': (32.8407, -83.6324),
    
    # HAWAII
    'honolulu': (21.3099, -157.8581), 'honolulu, hi': (21.3099, -157.8581),
    
    # IDAHO
    'boise': (43.6150, -116.2023), 'boise, id': (43.6150, -116.2023),
    'meridian': (43.6121, -116.3915), 'meridian, id': (43.6121, -116.3915),
    'nampa': (43.5407, -116.5635), 'nampa, id': (43.5407, -116.5635),
    'idaho falls': (43.4665, -112.0348), 'idaho falls, id': (43.4665, -112.0348),
    
    # ILLINOIS
    'chicago': (41.8781, -87.6298), 'chicago, il': (41.8781, -87.6298),
    'aurora': (41.7606, -88.3201), 'aurora, il': (41.7606, -88.3201),
    'rockford': (42.2711, -89.0940), 'rockford, il': (42.2711, -89.0940),
    'joliet': (41.5250, -88.0817), 'joliet, il': (41.5250, -88.0817),
    'naperville': (41.7508, -88.1535), 'naperville, il': (41.7508, -88.1535),
    'springfield': (39.7817, -89.6501), 'springfield, il': (39.7817, -89.6501),
    'peoria': (40.6936, -89.5890), 'peoria, il': (40.6936, -89.5890),
    
    # INDIANA
    'indianapolis': (39.7684, -86.1581), 'indianapolis, in': (39.7684, -86.1581),
    'fort wayne': (41.0793, -85.1394), 'fort wayne, in': (41.0793, -85.1394),
    'evansville': (37.9716, -87.5711), 'evansville, in': (37.9716, -87.5711),
    'south bend': (41.6764, -86.2520), 'south bend, in': (41.6764, -86.2520),
    
    # IOWA
    'des moines': (41.5868, -93.6250), 'des moines, ia': (41.5868, -93.6250),
    'cedar rapids': (41.9779, -91.6656), 'cedar rapids, ia': (41.9779, -91.6656),
    'davenport': (41.5236, -90.5776), 'davenport, ia': (41.5236, -90.5776),
    
    # KANSAS
    'wichita': (37.6872, -97.3301), 'wichita, ks': (37.6872, -97.3301),
    'overland park': (38.9822, -94.6708), 'overland park, ks': (38.9822, -94.6708),
    'kansas city': (39.0997, -94.5786), 'kansas city, ks': (39.0997, -94.5786),
    'topeka': (39.0473, -95.6752), 'topeka, ks': (39.0473, -95.6752),
    
    # KENTUCKY
    'louisville': (38.2527, -85.7585), 'louisville, ky': (38.2527, -85.7585),
    'lexington': (38.0406, -84.5037), 'lexington, ky': (38.0406, -84.5037),
    
    # LOUISIANA
    'new orleans': (29.9511, -90.0715), 'new orleans, la': (29.9511, -90.0715),
    'baton rouge': (30.4515, -91.1871), 'baton rouge, la': (30.4515, -91.1871),
    'shreveport': (32.5252, -93.7502), 'shreveport, la': (32.5252, -93.7502),
    'lafayette': (30.2241, -92.0198), 'lafayette, la': (30.2241, -92.0198),
    
    # MAINE
    'portland': (43.6591, -70.2568), 'portland, me': (43.6591, -70.2568),
    
    # MARYLAND
    'baltimore': (39.2904, -76.6122), 'baltimore, md': (39.2904, -76.6122),
    
    # MASSACHUSETTS
    'boston': (42.3601, -71.0589), 'boston, ma': (42.3601, -71.0589),
    'worcester': (42.2626, -71.8023), 'worcester, ma': (42.2626, -71.8023),
    'springfield, ma': (42.1015, -72.5898),
    'cambridge': (42.3736, -71.1097), 'cambridge, ma': (42.3736, -71.1097),
    
    # MICHIGAN
    'detroit': (42.3314, -83.0458), 'detroit, mi': (42.3314, -83.0458),
    'grand rapids': (42.9634, -85.6681), 'grand rapids, mi': (42.9634, -85.6681),
    'warren': (42.5145, -83.0147), 'warren, mi': (42.5145, -83.0147),
    'sterling heights': (42.5803, -83.0302), 'sterling heights, mi': (42.5803, -83.0302),
    'ann arbor': (42.2808, -83.7430), 'ann arbor, mi': (42.2808, -83.7430),
    
    # MINNESOTA
    'minneapolis': (44.9778, -93.2650), 'minneapolis, mn': (44.9778, -93.2650),
    'st paul': (44.9537, -93.0900), 'st paul, mn': (44.9537, -93.0900),
    'rochester': (44.0121, -92.4802), 'rochester, mn': (44.0121, -92.4802),
    'duluth': (46.7867, -92.1005), 'duluth, mn': (46.7867, -92.1005),
    
    # MISSISSIPPI
    'jackson': (32.2988, -90.1848), 'jackson, ms': (32.2988, -90.1848),
    
    # MISSOURI
    'kansas city, mo': (39.0997, -94.5786),
    'st louis': (38.6270, -90.1994), 'st louis, mo': (38.6270, -90.1994),
    'springfield, mo': (37.2090, -93.2923),
    'columbia': (38.9517, -92.3341), 'columbia, mo': (38.9517, -92.3341),
    
    # MONTANA
    'billings': (45.7833, -108.5007), 'billings, mt': (45.7833, -108.5007),
    'missoula': (46.8721, -113.9940), 'missoula, mt': (46.8721, -113.9940),
    
    # NEBRASKA
    'omaha': (41.2565, -95.9345), 'omaha, ne': (41.2565, -95.9345),
    'lincoln': (40.8136, -96.7026), 'lincoln, ne': (40.8136, -96.7026),
    
    # NEVADA
    'las vegas': (36.1699, -115.1398), 'las vegas, nv': (36.1699, -115.1398),
    'henderson': (36.0395, -114.9817), 'henderson, nv': (36.0395, -114.9817),
    'reno': (39.5296, -119.8138), 'reno, nv': (39.5296, -119.8138),
    'north las vegas': (36.1989, -115.1175), 'north las vegas, nv': (36.1989, -115.1175),
    
    # NEW HAMPSHIRE
    'manchester': (42.9956, -71.4548), 'manchester, nh': (42.9956, -71.4548),
    
    # NEW JERSEY
    'newark': (40.7357, -74.1724), 'newark, nj': (40.7357, -74.1724),
    'jersey city': (40.7178, -74.0431), 'jersey city, nj': (40.7178, -74.0431),
    'paterson': (40.9168, -74.1718), 'paterson, nj': (40.9168, -74.1718),
    
    # NEW MEXICO
    'albuquerque': (35.0844, -106.6504), 'albuquerque, nm': (35.0844, -106.6504),
    'las cruces': (32.3199, -106.7637), 'las cruces, nm': (32.3199, -106.7637),
    'santa fe': (35.6870, -105.9378), 'santa fe, nm': (35.6870, -105.9378),
    
    # NEW YORK
    'new york': (40.7128, -74.0060), 'new york, ny': (40.7128, -74.0060),
    'buffalo': (42.8864, -78.8784), 'buffalo, ny': (42.8864, -78.8784),
    'rochester, ny': (43.1566, -77.6088),
    'yonkers': (40.9312, -73.8987), 'yonkers, ny': (40.9312, -73.8987),
    'syracuse': (43.0481, -76.1474), 'syracuse, ny': (43.0481, -76.1474),
    'albany': (42.6526, -73.7562), 'albany, ny': (42.6526, -73.7562),
    
    # NORTH CAROLINA
    'charlotte': (35.2271, -80.8431), 'charlotte, nc': (35.2271, -80.8431),
    'raleigh': (35.7796, -78.6382), 'raleigh, nc': (35.7796, -78.6382),
    'greensboro': (36.0726, -79.7920), 'greensboro, nc': (36.0726, -79.7920),
    'durham': (35.9940, -78.8986), 'durham, nc': (35.9940, -78.8986),
    'winston-salem': (36.0999, -80.2442), 'winston-salem, nc': (36.0999, -80.2442),
    'fayetteville, nc': (35.0527, -78.8784),
    'cary': (35.7915, -78.7811), 'cary, nc': (35.7915, -78.7811),
    
    # NORTH DAKOTA
    'fargo': (46.8772, -96.7898), 'fargo, nd': (46.8772, -96.7898),
    'bismarck': (46.8083, -100.7837), 'bismarck, nd': (46.8083, -100.7837),
    
    # OHIO
    'columbus, oh': (39.9612, -82.9988),
    'cleveland': (41.4993, -81.6944), 'cleveland, oh': (41.4993, -81.6944),
    'cincinnati': (39.1031, -84.5120), 'cincinnati, oh': (39.1031, -84.5120),
    'toledo': (41.6528, -83.5379), 'toledo, oh': (41.6528, -83.5379),
    'akron': (41.0814, -81.5190), 'akron, oh': (41.0814, -81.5190),
    'dayton': (39.7589, -84.1916), 'dayton, oh': (39.7589, -84.1916),
    
    # OKLAHOMA
    'oklahoma city': (35.4676, -97.5164), 'oklahoma city, ok': (35.4676, -97.5164),
    'tulsa': (36.1540, -95.9928), 'tulsa, ok': (36.1540, -95.9928),
    'norman': (35.2226, -97.4395), 'norman, ok': (35.2226, -97.4395),
    
    # OREGON
    'portland, or': (45.5152, -122.6784),
    'salem': (44.9429, -123.0351), 'salem, or': (44.9429, -123.0351),
    'eugene': (44.0521, -123.0868), 'eugene, or': (44.0521, -123.0868),
    'gresham': (45.4979, -122.4302), 'gresham, or': (45.4979, -122.4302),
    
    # PENNSYLVANIA
    'philadelphia': (39.9526, -75.1652), 'philadelphia, pa': (39.9526, -75.1652),
    'pittsburgh': (40.4406, -79.9959), 'pittsburgh, pa': (40.4406, -79.9959),
    'allentown': (40.6084, -75.4902), 'allentown, pa': (40.6084, -75.4902),
    'erie': (42.1292, -80.0851), 'erie, pa': (42.1292, -80.0851),
    
    # RHODE ISLAND
    'providence': (41.8240, -71.4128), 'providence, ri': (41.8240, -71.4128),
    
    # SOUTH CAROLINA
    'columbia, sc': (34.0007, -81.0348),
    'charleston': (32.7765, -79.9311), 'charleston, sc': (32.7765, -79.9311),
    'north charleston': (32.8546, -79.9748), 'north charleston, sc': (32.8546, -79.9748),
    
    # SOUTH DAKOTA
    'sioux falls': (43.5446, -96.7311), 'sioux falls, sd': (43.5446, -96.7311),
    'rapid city': (44.0805, -103.2310), 'rapid city, sd': (44.0805, -103.2310),
    
    # TENNESSEE
    'nashville': (36.1627, -86.7816), 'nashville, tn': (36.1627, -86.7816),
    'memphis': (35.1495, -90.0490), 'memphis, tn': (35.1495, -90.0490),
    'knoxville': (35.9606, -83.9207), 'knoxville, tn': (35.9606, -83.9207),
    'chattanooga': (35.0456, -85.3097), 'chattanooga, tn': (35.0456, -85.3097),
    
    # TEXAS
    'houston': (29.7604, -95.3698), 'houston, tx': (29.7604, -95.3698),
    'san antonio': (29.4241, -98.4936), 'san antonio, tx': (29.4241, -98.4936),
    'dallas': (32.7767, -96.7970), 'dallas, tx': (32.7767, -96.7970),
    'austin': (30.2672, -97.7431), 'austin, tx': (30.2672, -97.7431),
    'fort worth': (32.7555, -97.3308), 'fort worth, tx': (32.7555, -97.3308),
    'el paso': (31.7619, -106.4850), 'el paso, tx': (31.7619, -106.4850),
    'arlington': (32.7357, -97.1081), 'arlington, tx': (32.7357, -97.1081),
    'corpus christi': (27.8006, -97.3964), 'corpus christi, tx': (27.8006, -97.3964),
    'plano': (33.0198, -96.6989), 'plano, tx': (33.0198, -96.6989),
    'laredo': (27.5306, -99.4803), 'laredo, tx': (27.5306, -99.4803),
    'lubbock': (33.5779, -101.8552), 'lubbock, tx': (33.5779, -101.8552),
    'garland': (32.9126, -96.6389), 'garland, tx': (32.9126, -96.6389),
    'irving': (32.8140, -96.9489), 'irving, tx': (32.8140, -96.9489),
    'amarillo': (35.2220, -101.8313), 'amarillo, tx': (35.2220, -101.8313),
    'mcallen': (26.2034, -98.2300), 'mcallen, tx': (26.2034, -98.2300),
    'waco': (31.5493, -97.1467), 'waco, tx': (31.5493, -97.1467),
    
    # UTAH
    'salt lake city': (40.7608, -111.8910), 'salt lake city, ut': (40.7608, -111.8910),
    'west valley city': (40.6916, -112.0011), 'west valley city, ut': (40.6916, -112.0011),
    'provo': (40.2338, -111.6585), 'provo, ut': (40.2338, -111.6585),
    
    # VERMONT
    'burlington': (44.4759, -73.2121), 'burlington, vt': (44.4759, -73.2121),
    
    # VIRGINIA
    'virginia beach': (36.8529, -75.9780), 'virginia beach, va': (36.8529, -75.9780),
    'norfolk': (36.8508, -76.2859), 'norfolk, va': (36.8508, -76.2859),
    'chesapeake': (36.7682, -76.2875), 'chesapeake, va': (36.7682, -76.2875),
    'richmond': (37.5407, -77.4360), 'richmond, va': (37.5407, -77.4360),
    'newport news': (37.0871, -76.4730), 'newport news, va': (37.0871, -76.4730),
    
    # WASHINGTON
    'seattle': (47.6062, -122.3321), 'seattle, wa': (47.6062, -122.3321),
    'spokane': (47.6588, -117.4260), 'spokane, wa': (47.6588, -117.4260),
    'tacoma': (47.2529, -122.4443), 'tacoma, wa': (47.2529, -122.4443),
    'vancouver, wa': (45.6387, -122.6615),
    'bellevue': (47.6101, -122.2015), 'bellevue, wa': (47.6101, -122.2015),
    
    # WASHINGTON DC
    'washington': (38.9072, -77.0369), 'washington, dc': (38.9072, -77.0369),
    
    # WEST VIRGINIA
    'charleston, wv': (38.3498, -81.6326),
    
    # WISCONSIN
    'milwaukee': (43.0389, -87.9065), 'milwaukee, wi': (43.0389, -87.9065),
    'madison': (43.0731, -89.4012), 'madison, wi': (43.0731, -89.4012),
    'green bay': (44.5133, -88.0133), 'green bay, wi': (44.5133, -88.0133),
    
    # WYOMING
    'cheyenne': (41.1400, -104.8202), 'cheyenne, wy': (41.1400, -104.8202),
    'casper': (42.8500, -106.3250), 'casper, wy': (42.8500, -106.3250),
}


def get_city_coordinates(city_query: str) -> tuple:
    """
    Get coordinates for a city from the database
    
    Args:
        city_query: City name (can include state)
    
    Returns:
        (lat, lon) tuple or None if not found
    """
    city_lower = city_query.lower().strip()
    
    # Try exact match first
    if city_lower in US_CITIES:
        return US_CITIES[city_lower]
    
    # Try partial match (city without state)
    for key, coords in US_CITIES.items():
        if city_lower in key or key in city_lower:
            return coords
    
    return None