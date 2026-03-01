"""
WiDS Datathon 2025 - EDA Script 2: Early Signal Validation (UPDATED)
=====================================================================

Purpose: Identify fire characteristics and keywords that predict evacuations

This version uses CLEANED data and has improved keyword detection.

Outputs:
- early_signals_report.csv: Predictive indicators
- signal_viz/: Visualizations
- keyword_analysis.csv: Text pattern analysis

Author: WiDS Team
Date: 2025-01-25 (Updated)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import json
import os
import re

# Create output directories
os.makedirs('signal_viz', exist_ok=True)
os.makedirs('04_results', exist_ok=True)

print("🔍 Starting Early Signal Validation (UPDATED)...")
print("="*80)

# ============================================================================
# STEP 1: Load CLEANED Data
# ============================================================================

print("\n1️⃣ Loading cleaned data files...")

# Check if cleaned data exists
if os.path.exists('01_raw_data/cleaned/geo_events_clean.csv'):
    print("   Using CLEANED data from 01_raw_data/cleaned/")
    geo_events = pd.read_csv('01_raw_data/cleaned/geo_events_clean.csv')
else:
    print("   ⚠️ Cleaned data not found, using raw data")
    print("   Run clean_all_data.py first for best results!")
    geo_events = pd.read_csv('01_raw_data/geo_events_geoevent.csv')
    
    # Quick cleaning
    def safe_json_parse(json_str):
        try:
            return json.loads(json_str) if pd.notna(json_str) else {}
        except:
            return {}
    
    geo_events['data_dict'] = geo_events['data'].apply(safe_json_parse)
    geo_events['acreage'] = geo_events['data_dict'].apply(lambda x: x.get('acreage', 0))
    geo_events['evacuation_orders'] = geo_events['data_dict'].apply(lambda x: x.get('evacuation_orders'))
    geo_events['evacuation_warnings'] = geo_events['data_dict'].apply(lambda x: x.get('evacuation_warnings'))
    geo_events['has_any_evac'] = (
        geo_events['evacuation_orders'].notna() | 
        geo_events['evacuation_warnings'].notna()
    )

geo_events['date_created'] = pd.to_datetime(geo_events['date_created'], errors='coerce')

print(f"   ✓ Loaded {len(geo_events):,} geo events")

# ============================================================================
# STEP 2: Create Evacuation Target Variable
# ============================================================================

print("\n2️⃣ Creating target variable...")

# Ensure evacuation flags exist
if 'has_any_evac' not in geo_events.columns:
    geo_events['has_any_evac'] = (
        geo_events.get('has_evac_order', False) | 
        geo_events.get('has_evac_warning', False)
    )

total_fires = len(geo_events)
with_evac = geo_events['has_any_evac'].sum()
without_evac = total_fires - with_evac

print(f"   ✓ Target variable created:")
print(f"      Fires WITH evacuations: {with_evac:,} ({with_evac/total_fires*100:.1f}%)")
print(f"      Fires WITHOUT evacuations: {without_evac:,} ({without_evac/total_fires*100:.1f}%)")

if with_evac < 10:
    print("\n   ⚠️ WARNING: Very few evacuations in dataset!")
    print("      This may limit predictive analysis.")

# ============================================================================
# STEP 3: Analyze Fire Size as Predictor
# ============================================================================

print("\n3️⃣ Analyzing fire size as evacuation predictor...")

# Get fires with valid acreage
if 'acreage' not in geo_events.columns:
    print("   ⚠️ Acreage column not found, skipping size analysis")
    fires_with_size = pd.DataFrame()
else:
    fires_with_size = geo_events[geo_events['acreage'] > 0].copy()
    
    if len(fires_with_size) > 0:
        evac_sizes = fires_with_size[fires_with_size['has_any_evac']]['acreage']
        no_evac_sizes = fires_with_size[~fires_with_size['has_any_evac']]['acreage']
        
        if len(evac_sizes) > 0 and len(no_evac_sizes) > 0:
            print(f"\n   🔥 Fire Sizes by Evacuation Status:")
            print(f"      WITH Evacuations ({len(evac_sizes):,} fires):")
            print(f"         Mean: {evac_sizes.mean():.1f} acres")
            print(f"         Median: {evac_sizes.median():.1f} acres")
            print(f"         75th percentile: {evac_sizes.quantile(0.75):.1f} acres")
            print(f"\n      WITHOUT Evacuations ({len(no_evac_sizes):,} fires):")
            print(f"         Mean: {no_evac_sizes.mean():.1f} acres")
            print(f"         Median: {no_evac_sizes.median():.1f} acres")
            print(f"         75th percentile: {no_evac_sizes.quantile(0.75):.1f} acres")
        else:
            print("   ⚠️ Insufficient data for size comparison")
            evac_sizes = pd.Series()
            no_evac_sizes = pd.Series()
    else:
        print("   ⚠️ No fires with valid acreage data")
        evac_sizes = pd.Series()
        no_evac_sizes = pd.Series()

# ============================================================================
# STEP 4: Enhanced Keyword Analysis
# ============================================================================

print("\n4️⃣ Analyzing incident names for predictive keywords...")

# Extract text content from name and address
def extract_text_content(row):
    """Extract all text for keyword analysis"""
    text_parts = []
    
    if pd.notna(row.get('name', None)):
        text_parts.append(str(row['name']).lower())
    
    if pd.notna(row.get('address', None)):
        text_parts.append(str(row['address']).lower())
    
    return ' '.join(text_parts)

geo_events['text_content'] = geo_events.apply(extract_text_content, axis=1)

# Expanded high-risk keyword list
HIGH_RISK_KEYWORDS = [
    # Weather/Wind
    'wind', 'winds', 'windy', 'wind-driven', 'winddriven',
    'gust', 'gusts', 'gusty',
    'red flag', 'red-flag', 'redflag',
    
    # Fire Behavior
    'rapid', 'fast', 'quickly', 'explosive', 'erratic', 'extreme',
    'spread', 'spreading', 'growth',
    'crown', 'crowning',
    'spot', 'spotting', 'spot fire', 'spotfire',
    
    # Structures/Development
    'structure', 'structures', 'home', 'homes', 'house', 'houses',
    'building', 'buildings', 'residential',
    'threat', 'threatens', 'threatening', 'threatened',
    
    # Topography
    'canyon', 'hill', 'hills', 'ridge', 'mountain',
    'steep', 'slope',
    
    # Evacuation-related (these will obviously correlate!)
    'evacuation', 'evacuate', 'evacuated', 'evacuating',
    'warning', 'order', 'mandatory',
    'shelter', 'flee',
    
    # Fire Names (patterns)
    'fire', 'wildfire', 'complex',
    
    # Size/Intensity
    'large', 'major', 'massive', 'huge',
    'acre', 'acres',
    'contained', 'containment', 'uncontained',
    
    # Other
    'vegetation', 'brush', 'grass', 'forest', 'timber',
    'urban', 'interface', 'wildland',
    'smoke', 'ash',
]

# Count keyword occurrences
print(f"   Searching for {len(HIGH_RISK_KEYWORDS)} keywords...")

keyword_results = []

for keyword in HIGH_RISK_KEYWORDS:
    # Create word boundary pattern
    pattern = r'\b' + re.escape(keyword) + r'\b'
    
    # Count matches
    evac_matches = geo_events[geo_events['has_any_evac']]['text_content'].str.contains(
        pattern, case=False, regex=True, na=False
    ).sum()
    
    no_evac_matches = geo_events[~geo_events['has_any_evac']]['text_content'].str.contains(
        pattern, case=False, regex=True, na=False
    ).sum()
    
    # Calculate rates
    total_evac = with_evac
    total_no_evac = without_evac
    
    evac_rate = (evac_matches / total_evac * 100) if total_evac > 0 else 0
    no_evac_rate = (no_evac_matches / total_no_evac * 100) if total_no_evac > 0 else 0
    
    # Calculate enrichment (how much more common in evacuated fires)
    enrichment = evac_rate / no_evac_rate if no_evac_rate > 0 else (
        float('inf') if evac_rate > 0 else 1.0
    )
    
    keyword_results.append({
        'keyword': keyword,
        'evac_count': evac_matches,
        'evac_rate_%': round(evac_rate, 2),
        'no_evac_count': no_evac_matches,
        'no_evac_rate_%': round(no_evac_rate, 2),
        'enrichment_ratio': round(enrichment, 2) if enrichment != float('inf') else 999.0,
        'total_appearances': evac_matches + no_evac_matches
    })

# Create DataFrame
keyword_df = pd.DataFrame(keyword_results)

# Sort by enrichment ratio
keyword_df = keyword_df.sort_values('enrichment_ratio', ascending=False)

# Filter out keywords that barely appear
keyword_df = keyword_df[keyword_df['total_appearances'] >= 5]

print(f"\n   📝 Top 15 Predictive Keywords:")
print(keyword_df.head(15)[['keyword', 'evac_rate_%', 'no_evac_rate_%', 'enrichment_ratio']].to_string(index=False))

# ============================================================================
# STEP 5: Create Visualizations
# ============================================================================

print("\n5️⃣ Creating visualizations...")

sns.set_style("whitegrid")

# VIZ 1: Fire Size Distribution (if data available)
if len(evac_sizes) > 0 and len(no_evac_sizes) > 0:
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Prepare data (remove extreme outliers for better viz)
    evac_plot = evac_sizes[evac_sizes < evac_sizes.quantile(0.95)]
    no_evac_plot = no_evac_sizes[no_evac_sizes < no_evac_sizes.quantile(0.95)]
    
    ax.hist([no_evac_plot, evac_plot], bins=30, label=['No Evacuation', 'With Evacuation'],
            alpha=0.7, color=['lightblue', 'coral'])
    ax.set_xlabel('Fire Size (acres)')
    ax.set_ylabel('Number of Fires')
    ax.set_title('Fire Size Distribution: Evacuated vs Non-Evacuated Fires')
    ax.legend()
    plt.tight_layout()
    plt.savefig('05_visualizations/signal_viz/fire_size_by_evacuation.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✓ Saved fire_size_by_evacuation.png")

# VIZ 2: Top Predictive Keywords
if len(keyword_df) >= 10:
    fig, ax = plt.subplots(figsize=(12, 8))
    
    top_keywords = keyword_df.head(15).copy()
    
    y_pos = np.arange(len(top_keywords))
    
    # Create grouped bar chart
    width = 0.35
    ax.barh(y_pos - width/2, top_keywords['evac_rate_%'], width, 
            label='With Evacuation', color='coral', alpha=0.8)
    ax.barh(y_pos + width/2, top_keywords['no_evac_rate_%'], width,
            label='Without Evacuation', color='lightblue', alpha=0.8)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(top_keywords['keyword'])
    ax.set_xlabel('Appearance Rate (%)')
    ax.set_title('Top 15 Predictive Keywords in Fire Incidents')
    ax.legend()
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig('05_visualizations/signal_viz/keyword_predictors.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✓ Saved keyword_predictors.png")

# VIZ 3: Keyword Enrichment Heatmap (top 10)
if len(keyword_df) >= 10:
    fig, ax = plt.subplots(figsize=(10, 8))
    
    top_10 = keyword_df.head(10)
    
    # Create matrix for heatmap
    data = top_10[['evac_rate_%', 'no_evac_rate_%']].T
    
    sns.heatmap(data, annot=True, fmt='.1f', cmap='YlOrRd', 
                xticklabels=top_10['keyword'],
                yticklabels=['With Evacuation', 'Without Evacuation'],
                ax=ax, cbar_kws={'label': 'Appearance Rate (%)'})
    
    ax.set_title('Keyword Appearance Rates: Top 10 Predictors')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('05_visualizations/signal_viz/keyword_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✓ Saved keyword_heatmap.png")

# ============================================================================
# STEP 6: Save Results
# ============================================================================

print("\n6️⃣ Saving analysis results...")

# Save keyword analysis
keyword_df.to_csv('04_results/keyword_analysis.csv', index=False)
print("   ✓ Saved keyword_analysis.csv")

# Save early signals summary
signals_data = {
    'signal_type': [],
    'value': []
}

signals_data['signal_type'].append('total_incidents')
signals_data['value'].append(len(geo_events))

signals_data['signal_type'].append('incidents_with_evacuations')
signals_data['value'].append(with_evac)

signals_data['signal_type'].append('evacuation_rate_%')
signals_data['value'].append(round(with_evac / total_fires * 100, 2))

if len(evac_sizes) > 0:
    signals_data['signal_type'].append('fire_size_mean_evac_acres')
    signals_data['value'].append(round(evac_sizes.mean(), 1))
    
    signals_data['signal_type'].append('fire_size_median_evac_acres')
    signals_data['value'].append(round(evac_sizes.median(), 1))

if len(no_evac_sizes) > 0:
    signals_data['signal_type'].append('fire_size_mean_no_evac_acres')
    signals_data['value'].append(round(no_evac_sizes.mean(), 1))
    
    signals_data['signal_type'].append('fire_size_median_no_evac_acres')
    signals_data['value'].append(round(no_evac_sizes.median(), 1))

signals_data['signal_type'].append('num_keywords_analyzed')
signals_data['value'].append(len(HIGH_RISK_KEYWORDS))

signals_data['signal_type'].append('num_predictive_keywords_found')
signals_data['value'].append(len(keyword_df))

signals_summary = pd.DataFrame(signals_data)
signals_summary.to_csv('04_results/early_signals_report.csv', index=False)
print("   ✓ Saved early_signals_report.csv")

# ============================================================================
# COMPLETION
# ============================================================================

print("\n" + "="*80)
print("✅ EARLY SIGNAL ANALYSIS COMPLETE!")
print("="*80)
print("\nGenerated Files:")
print("  📊 04_results/early_signals_report.csv - Summary statistics")
print("  📋 04_results/keyword_analysis.csv - Full keyword analysis")
print("  📁 05_visualizations/signal_viz/ - Visualization PNG files")

if len(keyword_df) > 0:
    top_keyword = keyword_df.iloc[0]
    print(f"\nKey Insights:")
    print(f"  • Top predictive keyword: '{top_keyword['keyword']}'")
    print(f"    - Appears in {top_keyword['evac_rate_%']:.1f}% of evacuated fires")
    print(f"    - Enrichment ratio: {top_keyword['enrichment_ratio']:.1f}x")
    print(f"  • Total keywords with predictive power: {len(keyword_df)}")
    print(f"  • Evacuation rate: {with_evac/total_fires*100:.1f}%")

print("\nNext Steps:")
print("  1. Review keyword_analysis.csv for dashboard trigger words")
print("  2. Use top keywords in 'Early Trigger Monitor' dashboard tab")
print("  3. Run eda_3_geographic_patterns.py for regional analysis")
print("="*80)