"""
build_real_delays.py  —  49ers Intelligence Lab
WiDS Datathon 2025

Extracts real evacuation timing and fire growth data from the WiDS changelog.

RUN FROM repo root:
  cd ~/widsdatathon
  python3 build_real_delays.py

OUTPUT:
  01_raw_data/processed/fire_events_with_svi_and_delays.csv
"""

import pandas as pd
import numpy as np
import json
import os
import warnings
warnings.filterwarnings('ignore')

BASE = os.path.expanduser("~/widsdatathon")
RAW  = os.path.join(BASE, "01_raw_data")
OUT  = os.path.join(RAW, "processed")
os.makedirs(OUT, exist_ok=True)

def rp(f): return os.path.join(RAW, f)
def op(f): return os.path.join(OUT, f)


# Step 1: Load fire events
print("=" * 60)
print("Step 1: Loading fire events...")
geo = pd.read_csv(rp("geo_events_geoevent.csv"), low_memory=False,
                  usecols=['id','name','is_active','lat','lng',
                           'notification_type','geo_event_type','date_created'])
geo = geo.rename(columns={'id':'geo_event_id','lat':'latitude','lng':'longitude'})
geo['geo_event_id'] = geo['geo_event_id'].astype(float).astype(int).astype(str)
geo['fire_start']   = pd.to_datetime(geo['date_created'], errors='coerce').dt.tz_localize('UTC')
print(f"  {len(geo):,} fire events loaded")


# Step 2: Parse changelog JSON
print("\nStep 2: Parsing changelog JSON (178k rows — ~3 min)...")
cl = pd.read_csv(rp("geo_events_geoeventchangelog.csv"), low_memory=False)
cl['timestamp'] = pd.to_datetime(cl['date_created'], errors='coerce', utc=True)

evac_orders     = []
evac_warnings   = []
evac_advisories = []
acreage_changes = []
containment_chg = []
spread_rate_chg = []

for _, row in cl.iterrows():
    try:
        gid = str(int(float(row['geo_event_id'])))
    except (ValueError, TypeError):
        continue

    ts = row['timestamp']

    try:
        changes = json.loads(str(row['changes']))
    except:
        continue

    if 'data.evacuation_orders' in changes:
        old_val, new_val = changes['data.evacuation_orders']
        if new_val and (not old_val or str(old_val) in ['', 'null', 'None', '[]']):
            evac_orders.append({'geo_event_id': gid, 'timestamp': ts, 'value': str(new_val)})

    if 'data.evacuation_warnings' in changes:
        old_val, new_val = changes['data.evacuation_warnings']
        if new_val and (not old_val or str(old_val) in ['', 'null', 'None', '[]']):
            evac_warnings.append({'geo_event_id': gid, 'timestamp': ts, 'value': str(new_val)})

    if 'data.evacuation_advisories' in changes:
        old_val, new_val = changes['data.evacuation_advisories']
        if new_val and (not old_val or str(old_val) in ['', 'null', 'None', '[]']):
            evac_advisories.append({'geo_event_id': gid, 'timestamp': ts, 'value': str(new_val)})

    if 'data.acreage' in changes:
        old_val, new_val = changes['data.acreage']
        try:
            acreage_changes.append({
                'geo_event_id': gid, 'timestamp': ts,
                'acres_from': float(old_val) if old_val else 0,
                'acres_to':   float(new_val) if new_val else 0,
            })
        except:
            pass

    if 'data.containment' in changes:
        old_val, new_val = changes['data.containment']
        try:
            containment_chg.append({
                'geo_event_id': gid, 'timestamp': ts,
                'containment_pct': float(new_val) if new_val else np.nan
            })
        except:
            pass

    if 'radio_traffic_indicates_rate_of_spread' in changes:
        old_val, new_val = changes['radio_traffic_indicates_rate_of_spread']
        if new_val:
            spread_rate_chg.append({
                'geo_event_id': gid, 'timestamp': ts,
                'spread_rate': str(new_val)
            })

print(f"  Evacuation orders activated:     {len(evac_orders):,}")
print(f"  Evacuation warnings activated:   {len(evac_warnings):,}")
print(f"  Evacuation advisories activated: {len(evac_advisories):,}")
print(f"  Acreage change records:          {len(acreage_changes):,}")
print(f"  Containment change records:      {len(containment_chg):,}")
print(f"  Spread rate records:             {len(spread_rate_chg):,}")


# Step 3: Earliest evac timestamp per fire
print("\nStep 3: Computing earliest evacuation timestamps...")

def earliest_per_fire(records, colname):
    if not records:
        return pd.DataFrame(columns=['geo_event_id', colname])
    df = pd.DataFrame(records)
    return (df.groupby('geo_event_id')['timestamp']
              .min().reset_index()
              .rename(columns={'timestamp': colname}))

orders_df     = earliest_per_fire(evac_orders,     'first_order_at')
warnings_df   = earliest_per_fire(evac_warnings,   'first_warning_at')
advisories_df = earliest_per_fire(evac_advisories, 'first_advisory_at')

print(f"  Fires with evac orders:     {len(orders_df):,}")
print(f"  Fires with evac warnings:   {len(warnings_df):,}")
print(f"  Fires with evac advisories: {len(advisories_df):,}")


# Step 4: Fire growth rate
print("\nStep 4: Computing fire growth rates...")
if acreage_changes:
    ac_df = pd.DataFrame(acreage_changes).sort_values(['geo_event_id','timestamp'])

    def fire_growth_stats(grp):
        grp        = grp.sort_values('timestamp')
        first_ts   = grp['timestamp'].iloc[0]
        last_ts    = grp['timestamp'].iloc[-1]
        max_acres  = grp['acres_to'].max()
        first_acres= grp['acres_from'].iloc[0]
        duration_h = max(((last_ts - first_ts).total_seconds() / 3600), 0.01)
        growth_rate= (max_acres - first_acres) / duration_h
        return pd.Series({
            'max_acres':                  max_acres,
            'first_acres':                first_acres,
            'growth_rate_acres_per_hour': max(growth_rate, 0),
            'n_acreage_updates':          len(grp),
            'fire_duration_hours':        duration_h,
        })

    growth_df = ac_df.groupby('geo_event_id').apply(fire_growth_stats).reset_index()
    print(f"  Growth stats for {len(growth_df):,} fires")
    print(f"  Median max acres:   {growth_df['max_acres'].median():.1f}")
    print(f"  Median growth rate: {growth_df['growth_rate_acres_per_hour'].median():.2f} acres/hr")
else:
    growth_df = pd.DataFrame(columns=['geo_event_id'])

# Step 5: Final containment
if containment_chg:
    cont_df    = pd.DataFrame(containment_chg)
    final_cont = (cont_df.groupby('geo_event_id')['containment_pct']
                         .last().reset_index()
                         .rename(columns={'containment_pct':'final_containment_pct'}))
else:
    final_cont = pd.DataFrame(columns=['geo_event_id'])

# Step 6: Spread rate
if spread_rate_chg:
    sr_df          = pd.DataFrame(spread_rate_chg)
    spread_summary = (sr_df.sort_values('timestamp')
                           .groupby('geo_event_id')['spread_rate']
                           .last().reset_index()
                           .rename(columns={'spread_rate':'last_spread_rate'}))
else:
    spread_summary = pd.DataFrame(columns=['geo_event_id'])


# Step 7: Join everything
print("\nStep 7: Building master table...")
result = geo.copy()

for df, label in [
    (orders_df,     'orders'),
    (warnings_df,   'warnings'),
    (advisories_df, 'advisories'),
    (growth_df,     'growth'),
    (final_cont,    'containment'),
    (spread_summary,'spread'),
]:
    if len(df) > 0 and 'geo_event_id' in df.columns:
        result = result.merge(df, on='geo_event_id', how='left')
        print(f"  Joined {label}: {len(df):,} rows")

for evac_type, ts_col in [('order',   'first_order_at'),
                           ('warning', 'first_warning_at'),
                           ('advisory','first_advisory_at')]:
    if ts_col not in result.columns:
        continue
    result[ts_col]    = pd.to_datetime(result[ts_col], utc=True)
    delay_col         = f'hours_to_{evac_type}'
    result[delay_col] = ((result[ts_col] - result['fire_start'])
                          .dt.total_seconds() / 3600).clip(lower=0, upper=720)
    valid = result[delay_col].notna().sum()
    med   = result[delay_col].median()
    print(f"  hours_to_{evac_type}: {valid:,} valid  |  median={med:.1f}h")

if 'hours_to_order' in result.columns:
    result['evacuation_delay_hours'] = result['hours_to_order']
elif 'hours_to_warning' in result.columns:
    result['evacuation_delay_hours'] = result['hours_to_warning']
else:
    result['evacuation_delay_hours'] = np.nan

result['evacuation_occurred']        = result['evacuation_delay_hours'].notna().astype(int)
result['exceeds_critical_threshold'] = (result['evacuation_delay_hours'] > 6).astype(int)


# Step 8: Join SVI
print("\nStep 8: Joining SVI...")
svi = pd.read_csv(os.path.join(RAW, "external", "SVI_2022_US_county.csv"), low_memory=False)
print(f"  {len(svi):,} counties loaded")

try:
    from scipy.spatial import cKDTree
    cc = pd.read_csv(os.path.join(BASE, "wids-caregiver-alert", "data", "CenPop2020_Mean_CO.txt"),
                     dtype={"STATEFP": str, "COUNTYFP": str})
    cc['FIPS']      = (cc['STATEFP'].str.zfill(2) + cc['COUNTYFP'].str.zfill(3)).astype(int)
    svi['FIPS']     = svi['FIPS'].astype(int)
    svi_coords      = svi.merge(cc[['FIPS','LATITUDE','LONGITUDE']], on='FIPS', how='inner')
    tree            = cKDTree(svi_coords[['LATITUDE','LONGITUDE']].values)
    _, idx          = tree.query(result[['latitude','longitude']].fillna(0).values, k=1)
    matched         = svi_coords.iloc[idx].reset_index(drop=True)

    result['county_fips']       = matched['FIPS'].values
    result['county_name']       = matched.get('COUNTY',    pd.Series(['']*len(matched))).values
    result['state']             = matched.get('STATE',     pd.Series(['']*len(matched))).values
    result['svi_score']         = matched['RPL_THEMES'].values
    result['svi_socioeconomic'] = matched.get('RPL_THEME1',pd.Series([np.nan]*len(matched))).values
    result['svi_household']     = matched.get('RPL_THEME2',pd.Series([np.nan]*len(matched))).values
    result['svi_minority']      = matched.get('RPL_THEME3',pd.Series([np.nan]*len(matched))).values
    result['svi_housing']       = matched.get('RPL_THEME4',pd.Series([np.nan]*len(matched))).values
    result['pop_age65']         = matched.get('E_AGE65',   pd.Series([0]*len(matched))).values
    result['pop_disability']    = matched.get('E_DISABL',  pd.Series([0]*len(matched))).values
    result['pop_poverty']       = matched.get('E_POV150',  pd.Series([0]*len(matched))).values
    result['pop_no_vehicle']    = matched.get('E_NOVEH',   pd.Series([0]*len(matched))).values
    result['is_vulnerable']     = (result['svi_score'] >= 0.75).astype(int)
    print(f"  SVI joined. Vulnerable: {result['is_vulnerable'].sum():,} / {len(result):,}")
except Exception as e:
    print(f"  SVI join error: {e}")
    result['svi_score']     = np.nan
    result['is_vulnerable'] = 0


# Step 9: Save
out_path = op("fire_events_with_svi_and_delays.csv")
result.to_csv(out_path, index=False)

print("\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)
print(f"Total fire events:       {len(result):,}")
print(f"With evacuation actions: {result['evacuation_occurred'].sum():,} "
      f"({result['evacuation_occurred'].mean()*100:.1f}%)")
print(f"In vulnerable counties:  {result['is_vulnerable'].sum():,} "
      f"({result['is_vulnerable'].mean()*100:.1f}%)")

evac = result[result['evacuation_occurred']==1]
if len(evac) > 0:
    d = evac['evacuation_delay_hours'].dropna()
    print(f"\nEvacuation delay — {len(d):,} fires with REAL data:")
    print(f"  Median:  {d.median():.1f}h")
    print(f"  Mean:    {d.mean():.1f}h")
    print(f"  90th %:  {d.quantile(0.9):.1f}h")
    vuln_d   = evac[evac['is_vulnerable']==1]['evacuation_delay_hours'].dropna()
    normal_d = evac[evac['is_vulnerable']==0]['evacuation_delay_hours'].dropna()
    if len(vuln_d) > 0 and len(normal_d) > 0 and normal_d.median() > 0:
        pct = (vuln_d.median() - normal_d.median()) / normal_d.median() * 100
        print(f"\nEquity finding:")
        print(f"  Vulnerable counties:     {vuln_d.median():.1f}h median")
        print(f"  Non-vulnerable counties: {normal_d.median():.1f}h median")
        print(f"  Vulnerable take {pct:+.0f}% {'longer' if pct>0 else 'shorter'}")

if 'growth_rate_acres_per_hour' in result.columns:
    g      = result['growth_rate_acres_per_hour'].dropna()
    vuln_g = result[result['is_vulnerable']==1]['growth_rate_acres_per_hour'].dropna()
    norm_g = result[result['is_vulnerable']==0]['growth_rate_acres_per_hour'].dropna()
    print(f"\nFire growth rate — {len(g):,} fires:")
    print(f"  Overall median: {g.median():.2f} acres/hr")
    if len(vuln_g) > 0 and len(norm_g) > 0 and norm_g.median() > 0:
        pct_g = (vuln_g.median() - norm_g.median()) / norm_g.median() * 100
        print(f"  Vulnerable counties:     {vuln_g.median():.2f} acres/hr")
        print(f"  Non-vulnerable counties: {norm_g.median():.2f} acres/hr")
        print(f"  Difference: {pct_g:+.0f}%")

print(f"\nSaved to: {out_path}")