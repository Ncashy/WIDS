"""
WiDS Datathon 2025 - EDA Script 1: Timeline & Delay Analysis
============================================================

Purpose: Calculate evacuation delay metrics and identify temporal patterns

Outputs:
- delay_metrics.csv: Key delay measurements per incident
- timeline_viz/: Visualizations of delays over time
- summary_stats.txt: Overall statistics

Author: WiDS Team
Date: 2025-01-25
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
import os

# Create output directories
os.makedirs('timeline_viz', exist_ok=True)

print("📊 Starting Timeline Analysis...")
print("="*80)

# ============================================================================
# STEP 1: Load Core Timeline Data
# ============================================================================

print("\n1️⃣ Loading data files...")

# Main incident records
geo_events = pd.read_csv('01_raw_data/geo_events_geoevent.csv')
print(f"   ✓ Loaded {len(geo_events):,} geo events")

# Incident change logs
geo_event_changelog = pd.read_csv('01_raw_data/geo_events_geoeventchangelog.csv')
print(f"   ✓ Loaded {len(geo_event_changelog):,} event changes")

# Zone-to-fire mappings
zone_event_map = pd.read_csv('01_raw_data/evac_zone_status_geo_event_map.csv')
print(f"   ✓ Loaded {len(zone_event_map):,} zone-event mappings")

# Fire perimeters
fire_perimeters = pd.read_csv('01_raw_data/fire_perimeters_gis_fireperimeter.csv')
print(f"   ✓ Loaded {len(fire_perimeters):,} fire perimeters")

# Evacuation zones (for current status)
evac_zones = pd.read_csv('01_raw_data/evac_zones_gis_evaczone.csv')
print(f"   ✓ Loaded {len(evac_zones):,} evacuation zones")

# ============================================================================
# STEP 2: Parse Timestamps
# ============================================================================

print("\n2️⃣ Parsing timestamps...")

# Convert all datetime columns
for df, name in [
    (geo_events, 'geo_events'),
    (geo_event_changelog, 'changelog'),
    (zone_event_map, 'zone_map'),
    (fire_perimeters, 'perimeters')
]:
    if 'date_created' in df.columns:
        df['date_created'] = pd.to_datetime(df['date_created'], errors='coerce')
    if 'date_modified' in df.columns:
        df['date_modified'] = pd.to_datetime(df['date_modified'], errors='coerce')
    print(f"   ✓ Parsed {name} timestamps")

# ============================================================================
# STEP 3: Extract Evacuation Info from JSON
# ============================================================================

print("\n3️⃣ Extracting evacuation data from JSON fields...")

def safe_json_parse(json_str):
    """Safely parse JSON string"""
    try:
        return json.loads(json_str) if pd.notna(json_str) else {}
    except:
        return {}

# Parse the 'data' JSON field in geo_events
geo_events['data_dict'] = geo_events['data'].apply(safe_json_parse)

# Extract evacuation-related fields
geo_events['evacuation_orders'] = geo_events['data_dict'].apply(
    lambda x: x.get('evacuation_orders')
)
geo_events['evacuation_warnings'] = geo_events['data_dict'].apply(
    lambda x: x.get('evacuation_warnings')
)
geo_events['acreage'] = geo_events['data_dict'].apply(
    lambda x: x.get('acreage', 0)
)
geo_events['containment'] = geo_events['data_dict'].apply(
    lambda x: x.get('containment', 0)
)

# Create binary flags
geo_events['has_evacuation_order'] = geo_events['evacuation_orders'].notna()
geo_events['has_evacuation_warning'] = geo_events['evacuation_warnings'].notna()
geo_events['has_any_evacuation'] = (
    geo_events['has_evacuation_order'] | geo_events['has_evacuation_warning']
)

print(f"   ✓ Found {geo_events['has_evacuation_order'].sum():,} incidents with evacuation orders")
print(f"   ✓ Found {geo_events['has_evacuation_warning'].sum():,} incidents with evacuation warnings")

# ============================================================================
# STEP 4: Analyze Incident Changelog for Status Changes
# ============================================================================

print("\n4️⃣ Analyzing incident status changes...")

# Parse changes JSON
geo_event_changelog['changes_dict'] = geo_event_changelog['changes'].apply(safe_json_parse)

# Extract specific change types
def extract_change_type(changes_dict):
    """Identify what type of change occurred"""
    if not changes_dict:
        return 'unknown'
    
    keys = list(changes_dict.keys())
    
    # Check for evacuation-related changes
    if any('evacuation' in k.lower() for k in keys):
        return 'evacuation_update'
    elif 'is_active' in keys:
        return 'status_change'
    elif 'name' in keys:
        return 'name_change'
    elif any('data.' in k for k in keys):
        return 'data_update'
    else:
        return 'other'

geo_event_changelog['change_type'] = geo_event_changelog['changes_dict'].apply(extract_change_type)

print("\n   Change Type Distribution:")
print(geo_event_changelog['change_type'].value_counts().to_string())

# ============================================================================
# STEP 5: Calculate Delay Metrics
# ============================================================================

print("\n5️⃣ Calculating delay metrics...")

# Metric 1: Fire Start to Zone Linkage Delay
# -------------------------------------------
# For each zone-event mapping, calculate time from fire start to zone link

zone_delays = zone_event_map.merge(
    geo_events[['id', 'date_created', 'name', 'has_any_evacuation']],
    left_on='geo_event_id',
    right_on='id',
    suffixes=('_zone_link', '_fire_start')
)

zone_delays['fire_to_zone_delay_hours'] = (
    zone_delays['date_created_zone_link'] - zone_delays['date_created_fire_start']
).dt.total_seconds() / 3600

# Remove negative delays (data quality issues)
zone_delays = zone_delays[zone_delays['fire_to_zone_delay_hours'] >= 0]

print(f"\n   🔥 Fire-to-Zone Linkage Delays:")
print(f"      Mean: {zone_delays['fire_to_zone_delay_hours'].mean():.2f} hours")
print(f"      Median: {zone_delays['fire_to_zone_delay_hours'].median():.2f} hours")
print(f"      Max: {zone_delays['fire_to_zone_delay_hours'].max():.2f} hours")
print(f"      90th percentile: {zone_delays['fire_to_zone_delay_hours'].quantile(0.9):.2f} hours")

# Metric 2: Active Fires - First Changelog Entry Delay
# -----------------------------------------------------
# Time from fire start to first logged change

first_changes = geo_event_changelog.groupby('geo_event_id')['date_created'].min().reset_index()
first_changes.columns = ['geo_event_id', 'first_change_time']

fire_change_delays = geo_events.merge(
    first_changes,
    left_on='id',
    right_on='geo_event_id',
    how='inner'
)

fire_change_delays['fire_to_first_change_hours'] = (
    fire_change_delays['first_change_time'] - fire_change_delays['date_created']
).dt.total_seconds() / 3600

fire_change_delays = fire_change_delays[fire_change_delays['fire_to_first_change_hours'] >= 0]

print(f"\n   📝 Fire-to-First-Change Delays:")
print(f"      Mean: {fire_change_delays['fire_to_first_change_hours'].mean():.2f} hours")
print(f"      Median: {fire_change_delays['fire_to_first_change_hours'].median():.2f} hours")

# ============================================================================
# STEP 6: Temporal Patterns
# ============================================================================

print("\n6️⃣ Analyzing temporal patterns...")

# Add time components to geo_events
geo_events['year'] = geo_events['date_created'].dt.year
geo_events['month'] = geo_events['date_created'].dt.month
geo_events['hour_of_day'] = geo_events['date_created'].dt.hour
geo_events['day_of_week'] = geo_events['date_created'].dt.dayofweek  # 0=Monday

print(f"\n   📅 Data Coverage:")
print(f"      Years: {geo_events['year'].min()} - {geo_events['year'].max()}")
print(f"      Total incidents: {len(geo_events):,}")
print(f"      Active incidents: {geo_events['is_active'].sum():,}")

# ============================================================================
# STEP 7: Create Visualizations
# ============================================================================

print("\n7️⃣ Creating visualizations...")

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# VIZ 1: Fire-to-Zone Delay Distribution
# ----------------------------------------
fig, ax = plt.subplots()
zone_delays['fire_to_zone_delay_hours'].hist(bins=50, edgecolor='black', ax=ax)
ax.set_xlabel('Delay (hours)')
ax.set_ylabel('Number of Zone Linkages')
ax.set_title('Distribution of Fire-to-Zone Linkage Delays')
ax.axvline(zone_delays['fire_to_zone_delay_hours'].median(), 
           color='red', linestyle='--', label=f'Median: {zone_delays["fire_to_zone_delay_hours"].median():.1f}h')
ax.legend()
plt.tight_layout()
plt.savefig('timeline_viz/fire_to_zone_delay_distribution.png', dpi=300)
plt.close()
print("   ✓ Saved fire_to_zone_delay_distribution.png")

# VIZ 2: Incidents by Year
# -------------------------
fig, ax = plt.subplots()
incident_counts = geo_events.groupby('year').size()
incident_counts.plot(kind='bar', ax=ax, color='steelblue')
ax.set_xlabel('Year')
ax.set_ylabel('Number of Incidents')
ax.set_title('Wildfire Incidents by Year')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('timeline_viz/incidents_by_year.png', dpi=300)
plt.close()
print("   ✓ Saved incidents_by_year.png")

# VIZ 3: Incidents by Hour of Day
# ---------------------------------
fig, ax = plt.subplots()
hourly_counts = geo_events.groupby('hour_of_day').size()
hourly_counts.plot(kind='bar', ax=ax, color='coral')
ax.set_xlabel('Hour of Day (0-23)')
ax.set_ylabel('Number of Incidents Reported')
ax.set_title('Fire Reports by Hour of Day')
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig('timeline_viz/incidents_by_hour.png', dpi=300)
plt.close()
print("   ✓ Saved incidents_by_hour.png")

# VIZ 4: Evacuation Status Breakdown
# ------------------------------------
fig, ax = plt.subplots()
evac_stats = pd.Series({
    'No Evacuation': (~geo_events['has_any_evacuation']).sum(),
    'Warning Only': (geo_events['has_evacuation_warning'] & ~geo_events['has_evacuation_order']).sum(),
    'Order Issued': geo_events['has_evacuation_order'].sum()
})
evac_stats.plot(kind='pie', ax=ax, autopct='%1.1f%%', startangle=90,
                colors=['lightgreen', 'orange', 'red'])
ax.set_ylabel('')
ax.set_title('Evacuation Status Distribution')
plt.tight_layout()
plt.savefig('timeline_viz/evacuation_status_breakdown.png', dpi=300)
plt.close()
print("   ✓ Saved evacuation_status_breakdown.png")

# ============================================================================
# STEP 8: Save Results
# ============================================================================

print("\n8️⃣ Saving analysis results...")

# Save delay metrics
delay_summary = pd.DataFrame({
    'metric': [
        'fire_to_zone_mean_hours',
        'fire_to_zone_median_hours',
        'fire_to_zone_90th_percentile_hours',
        'fire_to_first_change_mean_hours',
        'total_incidents',
        'incidents_with_evacuations',
        'total_zones_linked'
    ],
    'value': [
        zone_delays['fire_to_zone_delay_hours'].mean(),
        zone_delays['fire_to_zone_delay_hours'].median(),
        zone_delays['fire_to_zone_delay_hours'].quantile(0.9),
        fire_change_delays['fire_to_first_change_hours'].mean(),
        len(geo_events),
        geo_events['has_any_evacuation'].sum(),
        len(zone_delays)
    ]
})
delay_summary.to_csv('delay_metrics.csv', index=False)
print("   ✓ Saved delay_metrics.csv")

# Save detailed zone delays for dashboard
zone_delays_export = zone_delays[[
    'geo_event_id', 'name', 'uid_v2', 
    'date_created_fire_start', 'date_created_zone_link',
    'fire_to_zone_delay_hours', 'has_any_evacuation'
]].copy()
zone_delays_export.to_csv('zone_linkage_details.csv', index=False)
print("   ✓ Saved zone_linkage_details.csv")

# Save summary statistics
with open('summary_stats.txt', 'w') as f:
    f.write("WiDS Datathon 2025 - Timeline Analysis Summary\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    f.write("KEY FINDINGS:\n")
    f.write("-" * 80 + "\n")
    f.write(f"Total Wildfire Incidents: {len(geo_events):,}\n")
    f.write(f"Incidents with Evacuations: {geo_events['has_any_evacuation'].sum():,}\n")
    f.write(f"Total Zone-Fire Linkages: {len(zone_delays):,}\n\n")
    
    f.write("DELAY METRICS:\n")
    f.write("-" * 80 + "\n")
    f.write(f"Fire-to-Zone Linkage:\n")
    f.write(f"  Mean Delay: {zone_delays['fire_to_zone_delay_hours'].mean():.2f} hours\n")
    f.write(f"  Median Delay: {zone_delays['fire_to_zone_delay_hours'].median():.2f} hours\n")
    f.write(f"  90th Percentile: {zone_delays['fire_to_zone_delay_hours'].quantile(0.9):.2f} hours\n\n")
    
    f.write("TEMPORAL PATTERNS:\n")
    f.write("-" * 80 + "\n")
    f.write(f"Year Range: {geo_events['year'].min()} - {geo_events['year'].max()}\n")
    f.write(f"Most Common Hour: {geo_events['hour_of_day'].mode().values[0]}:00\n")
    f.write(f"Busiest Year: {geo_events['year'].value_counts().idxmax()} ({geo_events['year'].value_counts().max():,} incidents)\n")

print("   ✓ Saved summary_stats.txt")

# ============================================================================
# COMPLETION
# ============================================================================

print("\n" + "="*80)
print("✅ ANALYSIS COMPLETE!")
print("="*80)
print("\nGenerated Files:")
print("  📊 delay_metrics.csv - Summary statistics")
print("  📋 zone_linkage_details.csv - Detailed zone-fire linkages")
print("  📄 summary_stats.txt - Human-readable summary")
print("  📁 timeline_viz/ - 4 visualization PNG files")
print("\nNext Steps:")
print("  1. Review visualizations in timeline_viz/")
print("  2. Check delay_metrics.csv for dashboard KPIs")
print("  3. Run eda_2_early_signals.py for predictive analysis")
print("="*80)