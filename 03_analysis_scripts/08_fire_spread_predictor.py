"""
08_fire_spread_predictor.py
49ers Intelligence Lab — WiDS Datathon 2025

Trains a fire spread / evacuation delay prediction model on real WiDS data.
Outputs: models/fire_spread_model.pkl, models/evac_delay_model.pkl, models/feature_cols.json

Run from repo root:
    python3 03_analysis_scripts/08_fire_spread_predictor.py

Dependencies:
    pip install scikit-learn pandas numpy joblib xgboost shap --break-system-packages
"""

import pandas as pd
import numpy as np
import json
import os
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "01_raw_data" / "processed" / "fire_events_with_svi_and_delays.csv"
MODEL_DIR = REPO_ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading fire_events_with_svi_and_delays.csv ...")
df = pd.read_csv(DATA_PATH, low_memory=False)
print(f"  Loaded {len(df):,} rows, {df.shape[1]} columns")
print(f"  Columns: {list(df.columns[:20])} ...")

# ── Feature engineering ───────────────────────────────────────────────────────
print("\nEngineering features ...")

# Standardize column names to lowercase
df.columns = [c.lower().strip() for c in df.columns]

# --- Growth rate features ---
# Your data has acreage over time snapshots in changelog-derived columns
# Expected columns from 07_build_real_delays.py:
#   growth_rate_acres_per_hour, max_acres, initial_acres (or similar)
#   hours_to_order, hours_to_warning, hours_to_advisory
#   svi_rpl_themes (or rpl_themes), e_age65, e_pov150, e_disabl, e_noveh
#   latitude / lat, longitude / lon

# Flexible column detection
def find_col(df, candidates):
    """Return first matching column name (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None

col_growth   = find_col(df, ["growth_rate_acres_per_hour", "growth_rate", "acres_per_hour"])
col_acres    = find_col(df, ["max_acres", "acreage", "acres", "final_acres"])
col_svi      = find_col(df, ["rpl_themes", "svi_rpl_themes", "svi_score", "vulnerability"])
col_age65    = find_col(df, ["e_age65", "age65", "pct_age65"])
col_pov      = find_col(df, ["e_pov150", "pov150", "pct_poverty"])
col_disabl   = find_col(df, ["e_disabl", "disabl", "pct_disabled"])
col_noveh    = find_col(df, ["e_noveh", "noveh", "pct_no_vehicle"])
col_lat      = find_col(df, ["latitude", "lat", "y"])
col_lon      = find_col(df, ["longitude", "lon", "x"])
col_delay    = find_col(df, ["hours_to_order", "hours_to_evacuation", "evac_delay_hours"])

print(f"  Key columns detected:")
print(f"    growth_rate   → {col_growth}")
print(f"    acres         → {col_acres}")
print(f"    svi           → {col_svi}")
print(f"    delay (target)→ {col_delay}")
print(f"    lat/lon       → {col_lat} / {col_lon}")

# Build feature matrix
feature_cols = []
target_col   = col_delay  # Predict: hours until evacuation order

# Core fire behavior features
if col_growth:
    df["growth_rate"] = pd.to_numeric(df[col_growth], errors="coerce")
    feature_cols.append("growth_rate")

if col_acres:
    df["max_acres_log"] = np.log1p(pd.to_numeric(df[col_acres], errors="coerce"))
    feature_cols.append("max_acres_log")

# Vulnerability features
for col, name in [
    (col_svi,   "svi_score"),
    (col_age65, "pct_elderly"),
    (col_pov,   "pct_poverty"),
    (col_disabl,"pct_disabled"),
    (col_noveh, "pct_no_vehicle"),
]:
    if col:
        df[name] = pd.to_numeric(df[col], errors="coerce")
        feature_cols.append(name)

# Derived: high-vulnerability flag
if "svi_score" in df.columns:
    df["high_vuln"] = (df["svi_score"] >= 0.75).astype(int)
    feature_cols.append("high_vuln")

# Geographic features (rough region encoding)
if col_lat and col_lon:
    df["lat"] = pd.to_numeric(df[col_lat], errors="coerce")
    df["lon"] = pd.to_numeric(df[col_lon], errors="coerce")
    # US geographic regions (very rough)
    df["region_west"]      = ((df["lon"] < -105) & (df["lat"] > 30)).astype(int)
    df["region_southwest"] = ((df["lon"].between(-115, -95)) & (df["lat"].between(25, 38))).astype(int)
    df["region_california"]= ((df["lon"] < -114) & (df["lat"].between(32, 42))).astype(int)
    feature_cols += ["region_west", "region_southwest", "region_california"]

# Temporal features if date_created available
col_date = find_col(df, ["date_created", "fire_start", "start_date", "incident_date"])
if col_date:
    df["fire_date"] = pd.to_datetime(df[col_date], errors="coerce", utc=True)
    df["fire_month"]     = df["fire_date"].dt.month
    df["fire_doy"]       = df["fire_date"].dt.dayofyear
    df["fire_season"]    = df["fire_month"].map(
        lambda m: 0 if m in [12,1,2] else 1 if m in [3,4,5] else 2 if m in [6,7,8] else 3
    )
    feature_cols += ["fire_month", "fire_season"]

print(f"\n  Feature columns ({len(feature_cols)}): {feature_cols}")

# ── Model 1: Predict hours_to_evacuation_order ─────────────────────────────
print("\n── MODEL 1: Evacuation Delay Prediction ──────────────────────────────────")

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

if target_col:
    df_model = df[feature_cols + [target_col]].dropna()
    print(f"  Training rows (fires with real evac timing): {len(df_model):,}")

    if len(df_model) < 50:
        print("  ⚠  Too few labeled rows for supervised model. Check that hours_to_order is populated.")
        print("     Saving feature list only.")
    else:
        X = df_model[feature_cols].values
        y = df_model[target_col].values

        # Clip extreme outliers (top 1%) — keep 99th pct
        y_cap = np.percentile(y, 99)
        mask = y <= y_cap
        X, y = X[mask], y[mask]
        print(f"  After clipping outliers (>{y_cap:.1f}h): {len(y):,} rows")

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Try XGBoost first, fall back to GBM
        try:
            import xgboost as xgb
            delay_model = xgb.XGBRegressor(
                n_estimators=300,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                verbosity=0,
            )
            model_name = "XGBoost"
        except ImportError:
            delay_model = GradientBoostingRegressor(
                n_estimators=300, max_depth=4, learning_rate=0.05,
                subsample=0.8, random_state=42
            )
            model_name = "GradientBoosting"

        print(f"  Training {model_name} regressor ...")
        delay_model.fit(X_train, y_train)
        y_pred = delay_model.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        r2  = r2_score(y_test, y_pred)
        print(f"  Test MAE:  {mae:.2f} hours")
        print(f"  Test R²:   {r2:.3f}")

        # Save
        delay_model_path = MODEL_DIR / "evac_delay_model.pkl"
        joblib.dump(delay_model, delay_model_path)
        print(f"  ✓ Saved → {delay_model_path}")

        # SHAP feature importance (optional)
        try:
            import shap
            explainer = shap.TreeExplainer(delay_model)
            shap_vals = explainer.shap_values(X_test[:200])
            mean_abs_shap = np.abs(shap_vals).mean(axis=0)
            importance = sorted(zip(feature_cols, mean_abs_shap), key=lambda x: -x[1])
            print("\n  SHAP Feature Importance (top 10):")
            for feat, imp in importance[:10]:
                bar = "█" * int(imp * 5 / importance[0][1])
                print(f"    {feat:<25} {imp:.3f} {bar}")
        except Exception as e:
            print(f"  (SHAP skipped: {e})")

else:
    print("  ⚠  No evacuation delay column found — skipping supervised model.")
    print("     Ensure 07_build_real_delays.py has been run.")

# ── Model 2: Classify whether a fire will escalate (growth rate predictor) ──
print("\n── MODEL 2: Fire Escalation Classifier ───────────────────────────────────")
# Label: will this fire grow >100 acres/hour? (high-escalation)
if col_growth:
    df["escalates"] = (df["growth_rate"] > 100).astype(int)
    clf_features = [f for f in feature_cols if f != "growth_rate"]  # don't leak target

    if "svi_score" in clf_features and col_lat:
        df_clf = df[clf_features + ["escalates"]].dropna()
        print(f"  Classification rows: {len(df_clf):,}")
        print(f"  Escalation rate: {df_clf['escalates'].mean()*100:.1f}%")

        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report

        X_c = df_clf[clf_features].values
        y_c = df_clf["escalates"].values

        X_tr, X_te, y_tr, y_te = train_test_split(X_c, y_c, test_size=0.2,
                                                    random_state=42, stratify=y_c)

        clf = RandomForestClassifier(n_estimators=200, max_depth=6,
                                     class_weight="balanced", random_state=42, n_jobs=-1)
        clf.fit(X_tr, y_tr)
        y_pr = clf.predict(X_te)
        print(classification_report(y_te, y_pr, target_names=["Normal", "Escalating"]))

        clf_path = MODEL_DIR / "fire_escalation_model.pkl"
        joblib.dump(clf, clf_path)
        print(f"  ✓ Saved → {clf_path}")
    else:
        print("  Skipping (missing svi_score or lat columns)")
else:
    print("  Skipping (no growth_rate column)")

# ── Save feature metadata ────────────────────────────────────────────────────
meta = {
    "feature_cols": feature_cols,
    "target_col": target_col,
    "col_mapping": {
        "growth_rate_source":   col_growth,
        "acres_source":         col_acres,
        "svi_source":           col_svi,
        "delay_target_source":  target_col,
        "lat_source":           col_lat,
        "lon_source":           col_lon,
    },
    "training_stats": {
        "total_fires": int(len(df)),
        "fires_with_evac_timing": int(df[target_col].notna().sum()) if target_col else 0,
        "fires_with_growth_rate": int(df["growth_rate"].notna().sum()) if "growth_rate" in df.columns else 0,
    }
}

meta_path = MODEL_DIR / "feature_cols.json"
with open(meta_path, "w") as f:
    json.dump(meta, f, indent=2)
print(f"\n✓ Metadata saved → {meta_path}")
print("\n── Done. Models ready for fire_prediction_page.py ────────────────────────")
