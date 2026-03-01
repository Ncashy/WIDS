"""
WiDS Datathon 2025 - Data Cleaning & Preparation Script
========================================================

This script fixes all data quality issues before running analysis:
1. Improves state/county extraction from addresses
2. Cleans missing values
3. Validates date formats
4. Removes duplicates
5. Adds geographic identifiers

Run this BEFORE running any EDA scripts.

Author: WiDS Team
Date: 2025-01-25
"""

import pandas as pd
import numpy as np
import json
import re
from datetime import datetime
import os

print("🧹 WiDS Data Cleaning Pipeline")
print("="*80)

# ============================================================================
# STEP 1: Load Raw Data
# ============================================================================

print("\n1️⃣ Loading raw data files...")

data_files = {
    'geo_events': '01_raw_data/geo_events_geoevent.csv',
    'geo_event_changelog': '01_raw_data/geo_events_geoeventchangelog.csv',
    'zone_event_map': '01_raw_data/evac_zone_status_geo_event_map.csv',
    'evac_zones': '01_raw_data/evac_zones_gis_evaczone.csv',
    'fire_perimeters': '01_raw_data/fire_perimeters_gis_fireperimeter.csv',
    'fire_perimeter_changelog': '01_raw_data/fire_perimeters_gis_fireperimeterchangelog.csv',
    'external_events': '01_raw_data/geo_events_externalgeoevent.csv',
    'external_changelog': '01_raw_data/geo_events_externalgeoeventchangelog.csv'
}

# Load all data
dfs = {}
for name, path in data_files.items():
    if os.path.exists(path):
        dfs[name] = pd.read_csv(path)
        print(f"   ✓ Loaded {name}: {len(dfs[name]):,} rows")
    else:
        print(f"   ⚠️ Missing: {path}")

# ============================================================================
# STEP 2: Enhanced State/County Extraction
# ============================================================================

print("\n2️⃣ Improving geographic identification...")

def extract_state_enhanced(address):
    """
    Enhanced state extraction with multiple fallback strategies
    """
    if pd.isna(address) or str(address).strip() == '':
        return 'Unknown'
    
    address = str(address).strip()
    
    # Strategy 1: State abbreviation with word boundaries
    # Matches: "CA", "CA ", ", CA", "CA,"
    pattern1 = r'\b([A-Z]{2})\b'
    matches = re.findall(pattern1, address)
    
    valid_states = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
    }
    
    # Find first valid state code
    for match in matches:
        if match in valid_states:
            return match
    
    # Strategy 2: Full state names
    state_mapping = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY'
    }
    
    address_lower = address.lower()
    for full_name, abbrev in state_mapping.items():
        if full_name in address_lower:
            return abbrev
    
    # Strategy 3: Parse comma-separated parts
    # Format: "City, State ZIP" or "Address, City, State"
    parts = [p.strip() for p in address.split(',')]
    
    if len(parts) >= 2:
        # Check last part for state
        last_part = parts[-1].strip()
        
        # Remove ZIP code if present
        last_part_no_zip = re.sub(r'\d{5}(-\d{4})?', '', last_part).strip()
        
        # Check if what's left is a state code
        words = last_part_no_zip.split()
        if words:
            potential_state = words[0]
            if len(potential_state) == 2 and potential_state.upper() in valid_states:
                return potential_state.upper()
        
        # Check second-to-last part
        if len(parts) >= 3:
            second_last = parts[-2].strip()
            if len(second_last) == 2 and second_last.upper() in valid_states:
                return second_last.upper()
    
    return 'Unknown'

def extract_county_enhanced(address):
    """
    Enhanced county extraction
    """
    if pd.isna(address) or str(address).strip() == '':
        return 'Unknown'
    
    address = str(address)
    
    # Look for "County" keyword
    patterns = [
        r'([A-Z][a-zA-Z\s]+)\s+County',  # "Santa Clara County"
        r'County\s+of\s+([A-Z][a-zA-Z\s]+)',  # "County of Los Angeles"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, address)
        if match:
            county = match.group(1).strip()
            # Clean up extra spaces
            county = re.sub(r'\s+', ' ', county)
            return county
    
    return 'Unknown'

def extract_city(address):
    """
    Extract city from address
    """
    if pd.isna(address) or str(address).strip() == '':
        return 'Unknown'
    
    address = str(address).strip()
    
    # City is typically before the first comma
    parts = [p.strip() for p in address.split(',')]
    
    if len(parts) > 0:
        # First part might be street address or city
        first_part = parts[0]
        
        # If it contains numbers, it's likely a street address
        # City is probably in second part
        if re.search(r'\d+', first_part) and len(parts) > 1:
            return parts[1]
        else:
            return first_part
    
    return 'Unknown'

# Apply enhanced extraction to geo_events
if 'geo_events' in dfs:
    print("\n   Processing geo_events addresses...")
    dfs['geo_events']['state_clean'] = dfs['geo_events']['address'].apply(extract_state_enhanced)
    dfs['geo_events']['county_clean'] = dfs['geo_events']['address'].apply(extract_county_enhanced)
    dfs['geo_events']['city_clean'] = dfs['geo_events']['address'].apply(extract_city)
    
    # Report improvements
    original_unknown = (dfs['geo_events']['state_clean'] == 'Unknown').sum()
    total = len(dfs['geo_events'])
    
    print(f"   State extraction results:")
    print(f"      Total incidents: {total:,}")
    print(f"      States identified: {(total - original_unknown):,} ({(total - original_unknown)/total*100:.1f}%)")
    print(f"      Unknown remaining: {original_unknown:,} ({original_unknown/total*100:.1f}%)")
    print(f"\n   Top 10 states:")
    print(dfs['geo_events']['state_clean'].value_counts().head(10).to_string())

# ============================================================================
# STEP 3: Parse JSON Fields
# ============================================================================

print("\n3️⃣ Parsing JSON data fields...")

def safe_json_parse(json_str):
    """Safely parse JSON string"""
    try:
        if pd.isna(json_str):
            return {}
        return json.loads(json_str)
    except:
        return {}

if 'geo_events' in dfs:
    print("   Extracting fire characteristics...")
    dfs['geo_events']['data_dict'] = dfs['geo_events']['data'].apply(safe_json_parse)
    
    # Extract key fields
    dfs['geo_events']['acreage'] = dfs['geo_events']['data_dict'].apply(
        lambda x: x.get('acreage', 0)
    )
    dfs['geo_events']['containment'] = dfs['geo_events']['data_dict'].apply(
        lambda x: x.get('containment', 0)
    )
    dfs['geo_events']['evacuation_orders'] = dfs['geo_events']['data_dict'].apply(
        lambda x: x.get('evacuation_orders')
    )
    dfs['geo_events']['evacuation_warnings'] = dfs['geo_events']['data_dict'].apply(
        lambda x: x.get('evacuation_warnings')
    )
    dfs['geo_events']['is_prescribed'] = dfs['geo_events']['data_dict'].apply(
        lambda x: x.get('is_prescribed', False)
    )
    
    # Create evacuation flags
    dfs['geo_events']['has_evac_order'] = dfs['geo_events']['evacuation_orders'].notna()
    dfs['geo_events']['has_evac_warning'] = dfs['geo_events']['evacuation_warnings'].notna()
    dfs['geo_events']['has_any_evac'] = (
        dfs['geo_events']['has_evac_order'] | dfs['geo_events']['has_evac_warning']
    )
    
    print(f"      Fires with evacuation orders: {dfs['geo_events']['has_evac_order'].sum():,}")
    print(f"      Fires with evacuation warnings: {dfs['geo_events']['has_evac_warning'].sum():,}")
    print(f"      Fires with any evacuation: {dfs['geo_events']['has_any_evac'].sum():,}")

# ============================================================================
# STEP 4: Clean Timestamps
# ============================================================================

print("\n4️⃣ Cleaning timestamp columns...")

timestamp_cols = {
    'geo_events': ['date_created', 'date_modified'],
    'geo_event_changelog': ['date_created'],
    'zone_event_map': ['date_created'],
    'evac_zones': ['date_created', 'date_modified'],
    'fire_perimeters': ['date_created', 'date_modified', 'source_date_current'],
    'fire_perimeter_changelog': ['date_created'],
    'external_events': ['date_created', 'date_modified'],
    'external_changelog': ['date_created']
}

for df_name, cols in timestamp_cols.items():
    if df_name in dfs:
        for col in cols:
            if col in dfs[df_name].columns:
                dfs[df_name][col] = pd.to_datetime(dfs[df_name][col], errors='coerce')
        print(f"   ✓ Cleaned timestamps in {df_name}")

# ============================================================================
# STEP 5: Remove Duplicates
# ============================================================================

print("\n5️⃣ Checking for duplicates...")

for name, df in dfs.items():
    original_len = len(df)
    
    # Skip duplicate check for dataframes with dict columns
    # (data_dict column causes "unhashable type" error)
    if name == 'geo_events' and 'data_dict' in df.columns:
        print(f"   ⚠️ {name}: Skipping duplicate check (contains dict column)")
        continue
    
    try:
        # Check for complete duplicates
        df_deduped = df.drop_duplicates()
        duplicates = original_len - len(df_deduped)
        
        if duplicates > 0:
            print(f"   ⚠️ {name}: Found {duplicates} duplicate rows, removing...")
            dfs[name] = df_deduped
        else:
            print(f"   ✓ {name}: No duplicates")
    except TypeError as e:
        print(f"   ⚠️ {name}: Cannot check duplicates (contains unhashable columns)")
        continue

# ============================================================================
# STEP 6: Add Useful Derived Fields
# ============================================================================

print("\n6️⃣ Adding derived fields...")

if 'geo_events' in dfs:
    # Fire size categories
    dfs['geo_events']['fire_size_category'] = pd.cut(
        dfs['geo_events']['acreage'],
        bins=[0, 1, 10, 100, 1000, 10000, float('inf')],
        labels=['<1', '1-10', '10-100', '100-1K', '1K-10K', '10K+']
    )
    
    # Time components
    dfs['geo_events']['year'] = dfs['geo_events']['date_created'].dt.year
    dfs['geo_events']['month'] = dfs['geo_events']['date_created'].dt.month
    dfs['geo_events']['day_of_week'] = dfs['geo_events']['date_created'].dt.dayofweek
    dfs['geo_events']['hour_of_day'] = dfs['geo_events']['date_created'].dt.hour
    
    # Fire season (Apr-Oct in Northern Hemisphere)
    dfs['geo_events']['is_fire_season'] = dfs['geo_events']['month'].isin([4, 5, 6, 7, 8, 9, 10])
    
    print("   ✓ Added fire size categories")
    print("   ✓ Added temporal features")
    print("   ✓ Added fire season flag")

# ============================================================================
# STEP 7: Save Cleaned Data
# ============================================================================

print("\n7️⃣ Saving cleaned data files...")

# Create cleaned data directory
os.makedirs('01_raw_data/cleaned', exist_ok=True)

for name, df in dfs.items():
    output_path = f'01_raw_data/cleaned/{name}_clean.csv'
    df.to_csv(output_path, index=False)
    print(f"   ✓ Saved: {output_path} ({len(df):,} rows)")

# ============================================================================
# STEP 8: Generate Data Quality Report
# ============================================================================

print("\n8️⃣ Generating data quality report...")

report_lines = []
report_lines.append("WiDS Datathon 2025 - Data Quality Report")
report_lines.append("="*80)
report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
report_lines.append("")

# Overall statistics
report_lines.append("DATASET OVERVIEW:")
report_lines.append("-"*80)
for name, df in dfs.items():
    report_lines.append(f"{name}:")
    report_lines.append(f"  Rows: {len(df):,}")
    report_lines.append(f"  Columns: {len(df.columns)}")
    report_lines.append("")

# Geographic coverage
if 'geo_events' in dfs:
    report_lines.append("GEOGRAPHIC COVERAGE:")
    report_lines.append("-"*80)
    
    state_counts = dfs['geo_events']['state_clean'].value_counts()
    report_lines.append(f"Total Incidents: {len(dfs['geo_events']):,}")
    report_lines.append(f"States Identified: {len(state_counts[state_counts.index != 'Unknown']):,}")
    report_lines.append(f"Unknown States: {state_counts.get('Unknown', 0):,}")
    report_lines.append("")
    
    report_lines.append("Top 10 States by Incident Count:")
    for state, count in state_counts.head(10).items():
        pct = count / len(dfs['geo_events']) * 100
        report_lines.append(f"  {state:15s}: {count:6,} ({pct:5.1f}%)")
    report_lines.append("")

# Evacuation statistics
if 'geo_events' in dfs:
    report_lines.append("EVACUATION STATISTICS:")
    report_lines.append("-"*80)
    
    total_fires = len(dfs['geo_events'])
    with_evac = dfs['geo_events']['has_any_evac'].sum()
    
    report_lines.append(f"Total Fires: {total_fires:,}")
    report_lines.append(f"Fires with Evacuations: {with_evac:,} ({with_evac/total_fires*100:.1f}%)")
    report_lines.append(f"Fires with Orders: {dfs['geo_events']['has_evac_order'].sum():,}")
    report_lines.append(f"Fires with Warnings: {dfs['geo_events']['has_evac_warning'].sum():,}")
    report_lines.append("")

# Data quality issues
report_lines.append("DATA QUALITY NOTES:")
report_lines.append("-"*80)

if 'geo_events' in dfs:
    unknown_state_pct = (dfs['geo_events']['state_clean'] == 'Unknown').sum() / len(dfs['geo_events']) * 100
    
    if unknown_state_pct > 10:
        report_lines.append(f"⚠️ {unknown_state_pct:.1f}% of incidents have unknown state")
    
    low_evac_pct = (dfs['geo_events']['has_any_evac'].sum() / len(dfs['geo_events']) * 100)
    if low_evac_pct < 10:
        report_lines.append(f"⚠️ Only {low_evac_pct:.1f}% of fires resulted in evacuations")
    
    missing_acreage = (dfs['geo_events']['acreage'] == 0).sum()
    if missing_acreage > 0:
        report_lines.append(f"⚠️ {missing_acreage:,} fires have missing acreage data")

report_lines.append("")
report_lines.append("CLEANED FILES LOCATION:")
report_lines.append("-"*80)
report_lines.append("All cleaned files saved to: 01_raw_data/cleaned/")
report_lines.append("")
report_lines.append("NEXT STEPS:")
report_lines.append("-"*80)
report_lines.append("1. Review this report")
report_lines.append("2. Run analysis scripts using cleaned data")
report_lines.append("3. Build dashboard with improved geographic coverage")

# Save report
report_path = 'data_quality_report.txt'
with open(report_path, 'w') as f:
    f.write('\n'.join(report_lines))

print(f"   ✓ Saved: {report_path}")

# ============================================================================
# COMPLETION
# ============================================================================

print("\n" + "="*80)
print("✅ DATA CLEANING COMPLETE!")
print("="*80)
print("\nCleaned Files Location:")
print("  📁 01_raw_data/cleaned/")
print("\nGenerated Reports:")
print("  📄 data_quality_report.txt")
print("\nNext Steps:")
print("  1. Review data_quality_report.txt")
print("  2. Update EDA scripts to use cleaned data")
print("  3. Re-run all analyses:")
print("     python 03_analysis_scripts/eda_1_timeline_analysis.py")
print("     python 03_analysis_scripts/eda_2_early_signals.py")
print("     python 03_analysis_scripts/eda_3_geographic_patterns.py")
print("="*80)