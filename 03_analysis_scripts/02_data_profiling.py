import pandas as pd
import os

# List of your files
files = [
    'evac_zone_status_geo_event_map.csv',
    'evac_zones_gis_evaczone.csv',
    'evac_zones_gis_evacuationchangelog.csv',
    'fire_perimeters_gis_fireperimeter.csv',
    'fire_perimeters_gis_fireperimeterchangelog.csv',
    'geo_events_externalgeoevent.csv',
    'geo_events_externalgeoeventchangelog.csv',
    'geo_events_geoevent.csv',
    'geo_events_geoeventchangelog.csv'
]

output = []

for file in files:
    print(f"📊 Processing {file}...")
    
    try:
        # Read just first 1000 rows for speed
        df = pd.read_csv(file, nrows=1000)
        
        output.append(f"\n{'='*80}")
        output.append(f"FILE: {file}")
        output.append(f"{'='*80}")
        output.append(f"Total Columns: {len(df.columns)}")
        output.append(f"\n📋 COLUMNS:")
        for i, col in enumerate(df.columns, 1):
            dtype = df[col].dtype
            non_null = df[col].notna().sum()
            output.append(f"  {i}. {col} ({dtype}) - {non_null}/1000 non-null")
        
        output.append(f"\n🔍 SAMPLE DATA (first 3 rows):")
        output.append(df.head(3).to_string())
        
        # Look for key columns
        key_patterns = ['time', 'date', 'status', 'evac', 'warning', 'order', 'text', 'description', 'county']
        found_keys = [col for col in df.columns if any(pattern in col.lower() for pattern in key_patterns)]
        
        if found_keys:
            output.append(f"\n🔑 KEY COLUMNS DETECTED:")
            for col in found_keys:
                sample_vals = df[col].dropna().unique()[:3]
                output.append(f"  • {col}: {sample_vals}")
        
    except Exception as e:
        output.append(f"\n❌ ERROR reading {file}: {str(e)}")

# Save output
with open('data_profile.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("\n✅ Analysis complete! Check 'data_profile.txt'")