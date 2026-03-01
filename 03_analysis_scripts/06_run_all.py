#!/usr/bin/env python3
"""
WiDS Datathon 2025 - Run All Analysis (COMPLETE PIPELINE)
==========================================================

This script runs the complete analysis pipeline:
1. Cleans all data files
2. Runs timeline analysis
3. Runs early signal validation (FIXED)
4. Runs geographic pattern analysis

Run this ONE script instead of running each individually.

Author: WiDS Team
Date: 2025-01-25
"""

import subprocess
import sys
import os
from datetime import datetime

print("🔥 WiDS Datathon 2025 - Complete Analysis Pipeline")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# ============================================================================
# STEP 1: Clean Data
# ============================================================================

print("\n" + "="*80)
print("STEP 1/4: Data Cleaning")
print("="*80)

if os.path.exists('clean_all_data.py'):
    print("Running data cleaning script...")
    result = subprocess.run([sys.executable, 'clean_all_data.py'], capture_output=False)
    if result.returncode != 0:
        print("⚠️ Data cleaning had issues, but continuing...")
else:
    print("⚠️ clean_all_data.py not found, skipping cleaning step")

# ============================================================================
# STEP 2: Timeline Analysis
# ============================================================================

print("\n" + "="*80)
print("STEP 2/4: Timeline Analysis")
print("="*80)

if os.path.exists('03_analysis_scripts/eda_1_timeline_analysis.py'):
    print("Running timeline analysis...")
    result = subprocess.run([sys.executable, '03_analysis_scripts/eda_1_timeline_analysis.py'], 
                          capture_output=False)
    if result.returncode != 0:
        print("⚠️ Timeline analysis encountered errors")
else:
    print("❌ eda_1_timeline_analysis.py not found")

# ============================================================================
# STEP 3: Early Signal Validation (FIXED VERSION)
# ============================================================================

print("\n" + "="*80)
print("STEP 3/4: Early Signal Validation (FIXED)")
print("="*80)

if os.path.exists('eda_2_early_signals_FIXED.py'):
    print("Running FIXED early signal analysis...")
    result = subprocess.run([sys.executable, 'eda_2_early_signals_FIXED.py'], 
                          capture_output=False)
    if result.returncode != 0:
        print("⚠️ Early signal analysis encountered errors")
elif os.path.exists('03_analysis_scripts/eda_2_early_signals.py'):
    print("Running original early signal analysis...")
    result = subprocess.run([sys.executable, '03_analysis_scripts/eda_2_early_signals.py'], 
                          capture_output=False)
    if result.returncode != 0:
        print("⚠️ Early signal analysis encountered errors")
else:
    print("❌ eda_2_early_signals.py not found")

# ============================================================================
# STEP 4: Geographic Pattern Analysis
# ============================================================================

print("\n" + "="*80)
print("STEP 4/4: Geographic Pattern Analysis")
print("="*80)

if os.path.exists('03_analysis_scripts/eda_3_geographic_patterns.py'):
    print("Running geographic analysis...")
    result = subprocess.run([sys.executable, '03_analysis_scripts/eda_3_geographic_patterns.py'], 
                          capture_output=False)
    if result.returncode != 0:
        print("⚠️ Geographic analysis encountered errors")
else:
    print("❌ eda_3_geographic_patterns.py not found")

# ============================================================================
# COMPLETION SUMMARY
# ============================================================================

print("\n" + "="*80)
print("✅ COMPLETE ANALYSIS PIPELINE FINISHED")
print("="*80)
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Check what was generated
print("\n📊 Generated Outputs:")

output_checks = {
    'Data Quality Report': 'data_quality_report.txt',
    'Delay Metrics': '04_results/delay_metrics.csv',
    'Keyword Analysis': '04_results/keyword_analysis.csv',
    'Geographic Patterns': '04_results/geographic_patterns.csv',
    'Timeline Visualizations': '05_visualizations/timeline_viz/',
    'Signal Visualizations': '05_visualizations/signal_viz/',
    'Geographic Visualizations': '05_visualizations/geo_viz/'
}

all_good = True
for name, path in output_checks.items():
    if os.path.exists(path):
        if os.path.isdir(path):
            num_files = len([f for f in os.listdir(path) if f.endswith('.png')])
            print(f"  ✓ {name}: {num_files} files")
        else:
            print(f"  ✓ {name}")
    else:
        print(f"  ❌ {name} - NOT FOUND")
        all_good = False

print("\n" + "="*80)

if all_good:
    print("🎉 SUCCESS! All outputs generated.")
    print("\nNext Steps:")
    print("  1. Review data_quality_report.txt")
    print("  2. Check 04_results/ for CSV files")
    print("  3. View 05_visualizations/ for charts")
    print("  4. Start building Streamlit dashboard!")
else:
    print("⚠️ Some outputs missing. Review error messages above.")
    print("\nTroubleshooting:")
    print("  1. Check that all CSV files are in 01_raw_data/")
    print("  2. Ensure pandas, numpy, matplotlib are installed")
    print("  3. Review error messages for specific issues")

print("="*80)