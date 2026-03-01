"""
WiDS Datathon 2025 - EDA Script 3: Geographic Pattern Analysis
================================================================

Purpose: Identify geographic disparities in evacuation response times

Outputs:
- geographic_patterns.csv: Regional delay statistics
- geo_viz/: Map visualizations and regional comparisons
- equity_insights.txt: Findings on vulnerable areas

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
import re

# Create output directories
os.makedirs('geo_viz', exist_ok=True)

print("🗺️ Starting Geographic Pattern Analysis...")
print("="*80)

# ============================================================================
# STEP 1: Load Data
# ============================================================================

print("\n1️⃣ Loading data files...")

# Main incident records
geo_events = pd.read_csv('geo_events_geoevent.csv')
geo_events['date_created'] = pd.to_datetime(geo_events['date_created'])
print(f"   ✓ Loaded {len(geo_events):,} geo events")

# Zone-to-event mapping
zone_event_map = pd.read_csv('evac_zone_status_geo_event_map.csv')
zone_event_map['date_created'] = pd.to_datetime(zone_event_map['date_created'])
print(f"   ✓ Loaded {len(zone_event_map):,} zone-event mappings")

# Evacuation zones
evac_zones = pd.read_csv('evac_zones_gis_evaczone.csv')
evac_zones['date_created'] = pd.to_datetime(evac_zones['date_created'])
evac_zones['date_modified'] = pd.to_datetime(evac_zones['date_modified'])
print(f"   ✓ Loaded {len(evac_zones):,} evacuation zones")

# Fire perimeters
fire_perimeters = pd.read_csv('fire_perimeters_gis_fireperimeter.csv')
fire_perimeters['date_created'] = pd.to_datetime(fire_perimeters['date_created'])
print(f"   ✓ Loaded {len(fire_perimeters):,} fire perimeters")

# ============================================================================
# STEP 2: Extract Geographic Information
# ============================================================================

print("\n2️⃣ Extracting geographic identifiers...")

def safe_json_parse(json_str):
    try:
        return json.loads(json_str) if pd.notna(json_str) else {}
    except:
        return {}

# Parse geo_events data
geo_events['data_dict'] = geo_events['data'].apply(safe_json_parse)
geo_events['acreage'] = geo_events['data_dict'].apply(lambda x: x.get('acreage', 0))
geo_events['had_evacuation'] = (
    geo_events['data_dict'].apply(lambda x: x.get('evacuation_orders')).notna() | 
    geo_events['data_dict'].apply(lambda x: x.get('evacuation_warnings')).notna()
)

# Extract state/county from address field
def extract_state(address):
    """Extract state abbreviation from address string"""
    if pd.isna(address):
        return 'Unknown'
    
    # Look for state abbreviation pattern (e.g., ", CA ", ", California ")
    state_pattern = r',\s*([A-Z]{2})\s+'
    match = re.search(state_pattern, str(address))
    if match:
        return match.group(1)
    
    # Look for full state names
    state_names = {
        'California': 'CA', 'Oregon': 'OR', 'Washington': 'WA',
        'Arizona': 'AZ', 'Nevada': 'NV', 'Colorado': 'CO',
        'Montana': 'MT', 'Idaho': 'ID', 'New Mexico': 'NM',
        'Texas': 'TX', 'Utah': 'UT', 'Wyoming': 'WY'
    }
    
    for full_name, abbrev in state_names.items():
        if full_name in str(address):
            return abbrev
    
    return 'Unknown'

def extract_county(address):
    """Extract county from address string"""
    if pd.isna(address):
        return 'Unknown'
    
    # Simple heuristic: look for "County" keyword
    county_pattern = r'([A-Za-z\s]+)\s+County'
    match = re.search(county_pattern, str(address))
    if match:
        return match.group(1).strip()
    
    return 'Unknown'

geo_events['state'] = geo_events['address'].apply(extract_state)
geo_events['county'] = geo_events['address'].apply(extract_county)

print(f"\n   📍 Geographic Coverage:")
print(f"      States identified: {geo_events['state'].nunique()}")
print(f"      Top 5 states:")
state_counts = geo_events['state'].value_counts().head()
for state, count in state_counts.items():
    print(f"         {state}: {count:,} incidents")

# Extract zone regions from evac_zones
evac_zones['region_name'] = evac_zones['dataset_name']  # Using dataset_name as region identifier

print(f"\n   📍 Evacuation Zone Coverage:")
print(f"      Regions identified: {evac_zones['region_name'].nunique()}")
print(f"      Top 5 regions:")
region_counts = evac_zones['region_name'].value_counts().head()
for region, count in region_counts.items():
    print(f"         {region}: {count:,} zones")

# ============================================================================
# STEP 3: Calculate Geographic Delay Metrics
# ============================================================================

print("\n3️⃣ Calculating delay metrics by geography...")

# Merge zone mappings with fire events to get delays
zone_delays = zone_event_map.merge(
    geo_events[['id', 'date_created', 'state', 'county', 'had_evacuation']],
    left_on='geo_event_id',
    right_on='id',
    suffixes=('_zone_link', '_fire_start')
)

# Calculate delay
zone_delays['fire_to_zone_delay_hours'] = (
    zone_delays['date_created_zone_link'] - zone_delays['date_created_fire_start']
).dt.total_seconds() / 3600

# Remove negative delays
zone_delays = zone_delays[zone_delays['fire_to_zone_delay_hours'] >= 0]

# Aggregate by state
state_delays = zone_delays.groupby('state').agg({
    'fire_to_zone_delay_hours': ['count', 'mean', 'median', 'std'],
    'had_evacuation': 'sum'
}).round(2)
state_delays.columns = ['num_zones', 'mean_delay_hrs', 'median_delay_hrs', 'std_delay_hrs', 'num_evacuations']
state_delays = state_delays.reset_index()
state_delays = state_delays[state_delays['num_zones'] >= 10]  # Filter for statistical significance
state_delays = state_delays.sort_values('median_delay_hrs', ascending=False)

print(f"\n   ⏱️ Delay by State (median hours):")
for _, row in state_delays.head(10).iterrows():
    print(f"      {row['state']:12s}: {row['median_delay_hrs']:6.1f}h (n={int(row['num_zones'])})")

# Aggregate by county (for states with county data)
county_delays = zone_delays[zone_delays['county'] != 'Unknown'].copy()
county_delays['state_county'] = county_delays['state'] + ' - ' + county_delays['county']

county_summary = county_delays.groupby('state_county').agg({
    'fire_to_zone_delay_hours': ['count', 'mean', 'median'],
    'had_evacuation': 'sum'
}).round(2)
county_summary.columns = ['num_zones', 'mean_delay_hrs', 'median_delay_hrs', 'num_evacuations']
county_summary = county_summary.reset_index()
county_summary = county_summary[county_summary['num_zones'] >= 5]
county_summary = county_summary.sort_values('median_delay_hrs', ascending=False)

if len(county_summary) > 0:
    print(f"\n   ⏱️ Slowest Counties (median hours):")
    for _, row in county_summary.head(10).iterrows():
        print(f"      {row['state_county']:30s}: {row['median_delay_hrs']:6.1f}h (n={int(row['num_zones'])})")

# ============================================================================
# STEP 4: Analyze Zone Characteristics by Region
# ============================================================================

print("\n4️⃣ Analyzing evacuation zone patterns by region...")

# Merge zones with their event linkages
zones_with_events = evac_zones.merge(
    zone_event_map[['uid_v2', 'geo_event_id']],
    on='uid_v2',
    how='left'
)

# Count how many fires each zone has been linked to
zones_with_events['has_event'] = zones_with_events['geo_event_id'].notna()

region_zone_stats = zones_with_events.groupby('region_name').agg({
    'id': 'count',
    'is_active': 'sum',
    'has_event': 'sum',
    'external_status': lambda x: (x == 'Normal').sum()
}).reset_index()
region_zone_stats.columns = ['region', 'total_zones', 'active_zones', 'zones_with_fires', 'zones_status_normal']
region_zone_stats['pct_linked_to_fires'] = (
    region_zone_stats['zones_with_fires'] / region_zone_stats['total_zones'] * 100
).round(1)

print(f"\n   📊 Zone Activity by Region:")
print(region_zone_stats.sort_values('total_zones', ascending=False).head(10).to_string(index=False))

# ============================================================================
# STEP 5: Identify Vulnerable Areas
# ============================================================================

print("\n5️⃣ Identifying potentially vulnerable areas...")

# Vulnerable areas = high fire frequency + slow response
state_vulnerability = state_delays.copy()
state_vulnerability['fire_frequency_rank'] = state_vulnerability['num_zones'].rank(ascending=False)
state_vulnerability['delay_rank'] = state_vulnerability['median_delay_hrs'].rank(ascending=False)
state_vulnerability['vulnerability_score'] = (
    state_vulnerability['fire_frequency_rank'] + state_vulnerability['delay_rank']
)
state_vulnerability = state_vulnerability.sort_values('vulnerability_score', ascending=False)

print(f"\n   ⚠️ Highest Vulnerability Scores (high fires + slow response):")
print(state_vulnerability[['state', 'num_zones', 'median_delay_hrs', 'vulnerability_score']].head(10).to_string(index=False))

# ============================================================================
# STEP 6: Create Visualizations
# ============================================================================

print("\n6️⃣ Creating visualizations...")

sns.set_style("whitegrid")

# VIZ 1: Delay by State
# ----------------------
if len(state_delays) > 0:
    fig, ax = plt.subplots(figsize=(12, 6))
    
    top_states = state_delays.head(15)
    
    x_pos = np.arange(len(top_states))
    ax.barh(x_pos, top_states['median_delay_hrs'], color='coral', alpha=0.7)
    ax.set_yticks(x_pos)
    ax.set_yticklabels(top_states['state'])
    ax.set_xlabel('Median Delay (hours)')
    ax.set_title('Fire-to-Zone Linkage Delays by State (Top 15)')
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig('geo_viz/delays_by_state.png', dpi=300)
    plt.close()
    print("   ✓ Saved delays_by_state.png")

# VIZ 2: Fire Incidents by State
# --------------------------------
fig, ax = plt.subplots(figsize=(12, 6))

top_fire_states = geo_events['state'].value_counts().head(15)

x_pos = np.arange(len(top_fire_states))
ax.barh(x_pos, top_fire_states.values, color='steelblue', alpha=0.7)
ax.set_yticks(x_pos)
ax.set_yticklabels(top_fire_states.index)
ax.set_xlabel('Number of Incidents')
ax.set_title('Wildfire Incidents by State (Top 15)')
ax.invert_yaxis()

plt.tight_layout()
plt.savefig('geo_viz/incidents_by_state.png', dpi=300)
plt.close()
print("   ✓ Saved incidents_by_state.png")

# VIZ 3: County-Level Analysis (if data available)
# --------------------------------------------------
if len(county_summary) >= 10:
    fig, ax = plt.subplots(figsize=(14, 8))
    
    top_counties = county_summary.head(20)
    
    x_pos = np.arange(len(top_counties))
    ax.barh(x_pos, top_counties['median_delay_hrs'], color='darkorange', alpha=0.7)
    ax.set_yticks(x_pos)
    ax.set_yticklabels(top_counties['state_county'], fontsize=9)
    ax.set_xlabel('Median Delay (hours)')
    ax.set_title('Fire-to-Zone Linkage Delays by County (Top 20)')
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig('geo_viz/delays_by_county.png', dpi=300)
    plt.close()
    print("   ✓ Saved delays_by_county.png")

# VIZ 4: Vulnerability Score Map
# --------------------------------
fig, ax = plt.subplots(figsize=(12, 8))

top_vulnerable = state_vulnerability.head(15)

scatter = ax.scatter(
    top_vulnerable['median_delay_hrs'],
    top_vulnerable['num_zones'],
    s=top_vulnerable['vulnerability_score'] * 20,
    c=top_vulnerable['vulnerability_score'],
    cmap='YlOrRd',
    alpha=0.6,
    edgecolors='black'
)

for _, row in top_vulnerable.iterrows():
    ax.annotate(
        row['state'],
        (row['median_delay_hrs'], row['num_zones']),
        fontsize=9,
        ha='center'
    )

ax.set_xlabel('Median Delay (hours)')
ax.set_ylabel('Number of Zone-Fire Linkages')
ax.set_title('State Vulnerability: Fire Frequency vs Response Time\n(bubble size = vulnerability score)')
plt.colorbar(scatter, label='Vulnerability Score')

plt.tight_layout()
plt.savefig('geo_viz/vulnerability_scatter.png', dpi=300)
plt.close()
print("   ✓ Saved vulnerability_scatter.png")

# VIZ 5: Zone Activity by Region
# --------------------------------
fig, ax = plt.subplots(figsize=(12, 6))

top_regions = region_zone_stats.sort_values('total_zones', ascending=False).head(15)

x = np.arange(len(top_regions))
width = 0.35

ax.bar(x - width/2, top_regions['total_zones'], width, label='Total Zones', alpha=0.7, color='steelblue')
ax.bar(x + width/2, top_regions['zones_with_fires'], width, label='Zones with Fires', alpha=0.7, color='coral')

ax.set_xlabel('Region')
ax.set_ylabel('Number of Zones')
ax.set_title('Evacuation Zone Coverage by Region (Top 15)')
ax.set_xticks(x)
ax.set_xticklabels(top_regions['region'], rotation=45, ha='right', fontsize=8)
ax.legend()

plt.tight_layout()
plt.savefig('geo_viz/zones_by_region.png', dpi=300)
plt.close()
print("   ✓ Saved zones_by_region.png")

# ============================================================================
# STEP 7: Generate Equity Insights
# ============================================================================

print("\n7️⃣ Generating equity insights...")

equity_insights = []

# Overall statistics
overall_median = zone_delays['fire_to_zone_delay_hours'].median()
overall_mean = zone_delays['fire_to_zone_delay_hours'].mean()

equity_insights.append(f"OVERALL BASELINE:")
equity_insights.append(f"  Median delay across all areas: {overall_median:.1f} hours")
equity_insights.append(f"  Mean delay across all areas: {overall_mean:.1f} hours")
equity_insights.append(f"")

# Identify slowest vs fastest states
slowest_state = state_delays.iloc[0]
fastest_state = state_delays.iloc[-1]

equity_insights.append(f"GEOGRAPHIC DISPARITIES:")
equity_insights.append(f"  Slowest state: {slowest_state['state']} ({slowest_state['median_delay_hrs']:.1f}h median)")
equity_insights.append(f"  Fastest state: {fastest_state['state']} ({fastest_state['median_delay_hrs']:.1f}h median)")
equity_insights.append(f"  Disparity ratio: {slowest_state['median_delay_hrs'] / fastest_state['median_delay_hrs']:.1f}x")
equity_insights.append(f"")

# States above/below average
above_avg = state_delays[state_delays['median_delay_hrs'] > overall_median]
below_avg = state_delays[state_delays['median_delay_hrs'] <= overall_median]

equity_insights.append(f"PERFORMANCE TIERS:")
equity_insights.append(f"  States with ABOVE average delays: {len(above_avg)}")
equity_insights.append(f"  States with BELOW average delays: {len(below_avg)}")
equity_insights.append(f"")

# High-risk combinations
high_risk = state_vulnerability[
    (state_vulnerability['median_delay_hrs'] > overall_median) &
    (state_vulnerability['num_zones'] > state_vulnerability['num_zones'].median())
]

equity_insights.append(f"HIGH-RISK STATES (high fires + slow response):")
for _, row in high_risk.head(5).iterrows():
    equity_insights.append(f"  • {row['state']}: {int(row['num_zones'])} fires, {row['median_delay_hrs']:.1f}h median delay")

# ============================================================================
# STEP 8: Save Results
# ============================================================================

print("\n8️⃣ Saving analysis results...")

# Save state-level statistics
state_delays.to_csv('geographic_patterns.csv', index=False)
print("   ✓ Saved geographic_patterns.csv")

# Save county-level statistics (if available)
if len(county_summary) > 0:
    county_summary.to_csv('county_delays.csv', index=False)
    print("   ✓ Saved county_delays.csv")

# Save vulnerability scores
state_vulnerability.to_csv('vulnerability_scores.csv', index=False)
print("   ✓ Saved vulnerability_scores.csv")

# Save equity insights
with open('equity_insights.txt', 'w') as f:
    f.write("WiDS Datathon 2025 - Geographic Equity Analysis\n")
    f.write("=" * 80 + "\n\n")
    f.write("Analysis Date: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n")
    f.write("\n".join(equity_insights))
    
print("   ✓ Saved equity_insights.txt")

# ============================================================================
# COMPLETION
# ============================================================================

print("\n" + "="*80)
print("✅ GEOGRAPHIC ANALYSIS COMPLETE!")
print("="*80)
print("\nGenerated Files:")
print("  📊 geographic_patterns.csv - State-level delay statistics")
print("  📊 county_delays.csv - County-level analysis (if available)")
print("  📊 vulnerability_scores.csv - Combined risk assessment")
print("  📄 equity_insights.txt - Equity findings")
print("  📁 geo_viz/ - 5 visualization PNG files")
print("\nKey Findings:")
if len(state_delays) > 0:
    print(f"  • Slowest state: {slowest_state['state']} ({slowest_state['median_delay_hrs']:.1f}h)")
    print(f"  • Fastest state: {fastest_state['state']} ({fastest_state['median_delay_hrs']:.1f}h)")
    print(f"  • {len(high_risk)} states identified as high-risk (high frequency + slow response)")
print("\nNext Steps:")
print("  1. Review equity_insights.txt for dashboard messaging")
print("  2. Use vulnerability_scores.csv to prioritize dashboard features")
print("  3. Ready to build Streamlit prototype!")
print("="*80)