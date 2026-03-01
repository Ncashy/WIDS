# 49ers Intelligence Lab
## WiDS Datathon 2025 · Wildfire Caregiver Alert System
### Project Data & Code Reference — Context Document for Future Chats
### Last updated: February 22, 2026

---

## Project Overview
This system predicts evacuation delays for vulnerable populations during wildfires and routes proactive alerts to caregivers. It is the 49ers Intelligence Lab's submission to the WiDS Datathon 2025, currently in 2nd place.

**Core Research Question:** Do vulnerable populations (elderly, disabled, low-income) experience systematically longer evacuation delays during wildfires, and can a data-driven alert system reduce those delays?

---

## Key Findings

### Real Data Findings (WiDS 2021–2025 dataset — 653 fires with confirmed evac actions)
- Median time from fire start to evacuation order: **1.1 hours**
- Mean delay: **22.3 hours** (heavily right-skewed by slow-response fires)
- 90th percentile: **32.1 hours** — 1 in 10 fires takes over a day to get an order
- Fires in **vulnerable counties grow 17% faster** (11.71 vs 10.00 acres/hour)
- Vulnerable counties receive orders slightly faster at the median, but face faster-growing fires leaving less real response time
- 39.8% of all fire events occur in high-vulnerability counties (SVI ≥ 0.75)
- High-SVI evacuation zones take 28% longer to clear (median 23.7h vs 14.2h for low-SVI)

### Modeled/Projected Findings
- Caregiver alert system projects 0.85h earlier departure (per FEMA 2019 IPAWS study)
- At 65% adoption: projected 500–1,500 lives/year saved (grounded in USFA 375/yr baseline + Camp Fire 0.17% mortality rate)
- Getis-Ord Gi* hotspot analysis identifies evacuation corridor bottlenecks before they form

### Models Used
- **Cox Proportional Hazards** — models time-to-evacuation as function of SVI factors + fire proximity
- **Getis-Ord Gi*** — identifies statistically significant clusters of delayed evacuations
- **XGBoost regressor** — predicts hours_to_order, MAE 23.4h, R² 0.16, trained on 605 fires
- **Random Forest classifier** — predicts growth >100 ac/hr, recall 1.0 on escalating fires, trained on 19,392 fires

---

## Repository Structure
```
widsdatathon/
├── requirements.txt
├── .gitignore                              ← includes secrets.toml, large GeoJSONs
├── 01_raw_data/
├── 02_documentation/
│   └── WiDS_Context_Document.md           ← THIS FILE
├── 03_analysis_scripts/
│   ├── 01_clean_data.py
│   ├── 02_data_profiling.py
│   ├── 03_eda_timeline.py
│   ├── 04_eda_early_signals.py
│   ├── 05_eda_geographic.py
│   ├── 06_run_all.py
│   ├── 07_build_real_delays.py            ← main data pipeline
│   └── 08_fire_spread_predictor.py        ← trains evac delay + escalation models
├── 04_results/
├── 05_visualizations/
├── 06_working_files/
├── models/                                ← NOT in git (generate locally)
│   ├── evac_delay_model.pkl               ← XGBoost regressor, MAE 23.4h, R² 0.16
│   ├── fire_escalation_model.pkl          ← Random Forest classifier, recall 1.0
│   └── feature_cols.json                 ← feature metadata + training stats
└── wids-caregiver-alert/src/              ← Streamlit Community Cloud points here
    ├── wildfire_alert_dashboard.py        ← MAIN APP (entry point)
    ├── live_incident_feed.py              ← Fire data loader: WiDS → FIRMS public CSV → none
    ├── command_dashboard_page.py          ← Emergency Worker dashboard (NEW Feb 2026)
    ├── caregiver_start_page.py            ← Caregiver landing page (NEW Feb 2026)
    ├── fire_prediction_page.py            ← Fire Spread Predictor (dispatcher + analyst)
    ├── real_data_insights.py              ← Analyst data visualizations (rewritten Feb 2026)
    ├── impact_projection_page.py          ← Impact projection (real data grounded, Feb 2026)
    ├── risk_calculator_page.py            ← Evacuation risk calculator (rewritten Feb 2026)
    ├── coverage_analysis_page.py          ← Merged agency coverage + alert equity (NEW Feb 2026)
    ├── zone_duration_page.py              ← Zone duration analysis (NEW Feb 2026)
    ├── geo_map.py
    ├── fire_data_integration.py
    ├── evacuation_planner_page.py
    ├── evacuation_routes.py
    ├── directions_page.py                 ← Has known syntax error on line ~1301 (see Known Issues)
    ├── osm_routing.py
    ├── transit_and_safezones.py
    ├── us_cities_database.py
    ├── us_territories_data.py
    ├── 49ers_logo.png                     ← Logo file, shown on login + sidebar
    ├── usfa-registry-national.csv         ← in git (~5MB)
    ├── requirements.txt
    ├── __init__.py
    └── .streamlit/secrets.toml           ← NOT in git

    ── REMOVED in Feb 2026 refactor ──
    ├── agency_coverage_page.py            ← merged into coverage_analysis_page.py
    └── alert_channel_equity_page.py       ← merged into coverage_analysis_page.py
```

---

## Raw Data Files (01_raw_data/)
Large files — do not commit to git. Generate locally and copy processed outputs to src/.

| File | Size | What It Is | Used By |
|------|------|------------|---------|
| evac_zones_gis_evaczone.csv | 195 MB | 37,458 evacuation zone polygons. WKT geometry, status, external_status. Source: Genasys Protect. | preprocess_geo_data.py → evac_zones_map.geojson |
| evac_zone_status_geo_event_map.csv | 330 KB | Links evac zones to fire events. 4,429 rows. uid_v2 + geo_event_id + date_created. | 07_build_real_delays.py |
| evac_zones_gis_evaczonechangelog.csv | 332 MB | Full change history for every evac zone. 68,900 entries. | zone_duration_page.py (degrades to known stats when not deployed) |
| fire_perimeters_gis_fireperimeter.csv | 381 MB | 6,207 fire perimeter polygons from NIFC/FIRIS. 67% approved. | preprocess_geo_data.py → fire_perimeters_approved.geojson |
| geo_events_geoevent.csv | varies | 62,696 fire events 2021–2025. name, is_active, lat/lng, notification_type, date_created. Master join key. | live_incident_feed.py, 07_build_real_delays.py |
| geo_events_geoeventchangelog.csv | 1.03M rows | JSON changes column. Key fields: data.evacuation_orders (3,430), data.evacuation_warnings (3,966), data.evacuation_advisories (1,618), data.acreage (38,678), data.containment (25,505). **Real evacuation timing source.** | 07_build_real_delays.py |
| geo_events_externalgeoevent.csv | 1.5M rows | Alert channel distribution. 63% bots-extra-alerts, 7% bots-alertwest-ai. | coverage_analysis_page.py |
| geo_events_externalgeoeventchangelog.csv | varies | Cross-references WatchDuty with CAL FIRE, PulsePoint, WildCAD. external_source: 37% wildcad, 34% null, 29% other. | coverage_analysis_page.py |
| usfa-registry-national.csv | ~5 MB | ~35,000 US fire departments. Name, city, state, county, type, stations, FF counts. **Copy to src/.** | command_dashboard_page.py |

---

## Processed Outputs (01_raw_data/processed/)
Generated locally — copy GeoJSON files to src/ for dashboard map. Large GeoJSONs are gitignored.

| File | Size | How Made | Notes |
|------|------|----------|-------|
| evac_zones_map.geojson | 32.2 MB | preprocess_geo_data.py — 3 decimal precision, max 50 vertices/ring | **Copy to src/. Gitignored (too large).** |
| fire_perimeters_approved.geojson | 36.1 MB | preprocess_geo_data.py — approved status only | **Copy to src/. Gitignored (too large).** |
| evac_zones_active.geojson | 171 MB | preprocess_geo_data.py intermediate | **Gitignored. Too large for GitHub.** |
| evac_zones_slim.geojson | 98.6 MB | preprocess_geo_data.py intermediate | **Gitignored. Too large for GitHub.** |
| geo_events_summary.csv | 1.5 MB | preprocess_geo_data.py Step 3 | 62,696 rows lightweight lookup |
| fire_events_with_svi_and_delays.csv | 15 MB | 07_build_real_delays.py | **Core analysis dataset. Force-committed with `git add -f`.** 653 fires with real evac timing, 19,392 with growth rates, SVI for all 62,696. |

**Copy GeoJSON and USFA to src/ after generating:**
```bash
cp 01_raw_data/processed/evac_zones_map.geojson wids-caregiver-alert/src/
cp 01_raw_data/processed/fire_perimeters_approved.geojson wids-caregiver-alert/src/
cp 01_raw_data/usfa-registry-national.csv wids-caregiver-alert/src/
```

---

## Critical Join Chain

```
geo_events_geoeventchangelog.csv
  JSON changes → data.evacuation_orders / warnings / advisories
  geo_event_id: normalize float string "22429.0" → "22429" with str(int(float(x)))
        ↓ join on geo_event_id
geo_events_geoevent.csv
  date_created: tz_localize('UTC') — file is timezone-naive
  lat/lng → spatial join to SVI via cKDTree nearest county
        ↓ subtract timestamps → real hours_to_order/warning/advisory

evac_zone_status_geo_event_map.csv (uid_v2 + geo_event_id + date_created)
        ↓ join on uid_v2
evac_zones_gis_evaczone.csv
  external_status: primary — full strings ("Evacuation Order", "Normal", "Advisory")
  status: fallback — plural lowercase ("warnings", "advisories", "orders")
```

| Left | Right | Key |
|------|-------|-----|
| evac_zones_gis_evaczone | evac_zone_status_geo_event_map | uid_v2 |
| evac_zone_status_geo_event_map | geo_events_geoevent | geo_event_id |
| fire_perimeters_gis_fireperimeter | geo_events_geoevent | geo_event_id |
| geo_events_geoevent | SVI_2022_US_county | Spatial: lat/lng → nearest FIPS via cKDTree |
| SVI_2022_US_county | CenPop2020_Mean_CO.txt | FIPS (5-digit) |

---

## Scripts

| Script | Location | What It Does |
|--------|----------|--------------|
| 07_build_real_delays.py | 03_analysis_scripts/ | **Main data pipeline.** Parses 178k changelog JSON rows, extracts real evac timestamps, computes fire growth rates, joins SVI. Outputs fire_events_with_svi_and_delays.csv. ~3 min. Run from repo root. |
| 08_fire_spread_predictor.py | 03_analysis_scripts/ | Trains evac delay + escalation models. Outputs to models/. ~2 min. Run from repo root. |
| 01_clean_data.py | 03_analysis_scripts/ | Data cleaning |
| 02_data_profiling.py | 03_analysis_scripts/ | Data profiling |
| 03_eda_timeline.py | 03_analysis_scripts/ | Timeline EDA |
| 04_eda_early_signals.py | 03_analysis_scripts/ | Early signals EDA |
| 05_eda_geographic.py | 03_analysis_scripts/ | Geographic patterns EDA |
| 06_run_all.py | 03_analysis_scripts/ | Runs full analysis pipeline |

**Run build_real_delays.py:**
```bash
cd ~/widsdatathon
python3 03_analysis_scripts/07_build_real_delays.py
```

---

## How to Run Dashboard

```bash
cd /Users/lena/widsdatathon/wids-caregiver-alert/src
python3 -m streamlit run wildfire_alert_dashboard.py

# Install dependencies
pip3 install streamlit anthropic folium streamlit-folium plotly pandas numpy shapely scipy lifelines --break-system-packages
```

---

## Streamlit Community Cloud

- **Repo:** github.com/layesh1/widsdatathon
- **Branch:** main
- **Main file:** wids-caregiver-alert/src/wildfire_alert_dashboard.py
- **Logs:** share.streamlit.io → app → Manage app → Logs
- Auto-deploys on every push to main

---

## Dashboard Pages & Role Access

| Page | Role | Data Sources | Notes |
|------|------|-------------|-------|
| Command Dashboard | Emergency Worker | NASA FIRMS, SVI, USFA, GeoJSON | 3 tabs: Fire Map / Evacuee Status Tracker / Fire Dept Resources. Resource gap analysis joins USFA career FF with SVI by county. |
| Start Here | Caregiver/Evacuee | NASA FIRMS public CSV, FEMA shelters API, Nominatim geocoder | Enter address → check fires within X miles → show nearest open shelters → confirm evacuation (feeds dispatcher tracker) |
| Evacuation Planner | Caregiver/Evacuee | fire_data, vulnerable_populations | evacuation_planner_page.py — call uses inspect to handle signature differences |
| Safe Routes & Transit | Caregiver/Evacuee | OSRM, fire_data | directions_page.py — has syntax error on line ~1301, see Known Issues |
| Dashboard | Analyst | NASA FIRMS, SVI, real insights | Overview KPIs + real_data_insights.py |
| Equity Analysis | Analyst | fire_events_with_svi_and_delays.csv | Falls back to real_data_insights.py if equity_analysis_page.py not found |
| Risk Calculator | Analyst | User inputs, FEMA evac time estimates | FEMA mobility times, safety buffer formula, live FIRMS proximity check |
| Impact Projection | Analyst | Real baselines + sliders | USFA 375/yr deaths, Camp Fire 0.17% mortality, FEMA 0.85h lead time |
| Coverage Analysis | Analyst | geo_events_externalgeoevent*.csv, SVI | Merged from agency_coverage_page + alert_channel_equity_page. 3 tabs: Agency Gaps / Alert Channel Equity / Combined Risk Index |
| Zone Duration | Analyst | evac_zones_gis_evaczonechangelog.csv | Degrades gracefully to known stats when 332MB file not deployed |
| Fire Predictor | Emergency Worker + Analyst | fire_events_with_svi_and_delays.csv, FIRMS | Tab 1: forward-looking hotspot forecast. Tab 2: known fire analysis. Call as render_fire_prediction_page(role=username) — no other kwargs |
| AI Assistant | All roles | Anthropic claude-sonnet-4-6 | EVAC-OPS (dispatcher) / SAFE-PATH (caregiver) / DATA-LAB (analyst) personas |
| About | Analyst | — | Real findings cited with sources |

---

## Live Fire Data Pipeline (live_incident_feed.py)

Priority order — tries each source, uses first that returns data:
1. **WiDS geo_events_geoevent.csv** (local) — 🟢 shown if active rows found
2. **NASA FIRMS VIIRS public CSV** (no API key needed) — 🟡 shown. URL: `https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv`
3. **NASA FIRMS MODIS public CSV** (fallback) — 🟡 shown
4. **No data** — ⚪ shown, pages degrade gracefully

Cached 5 minutes (TTL=300). geo_events_geoevent.csv is NOT deployed to Streamlit Cloud — FIRMS is the live source in production.

---

## Caregiver ↔ Dispatcher Status Sync

The evacuee tracker in the Command Dashboard and the confirmation form on the Start Here page share `st.session_state.evacuee_list`. When a caregiver confirms their person has evacuated on Start Here, the dispatcher's tracker updates automatically within the same session. In a full deployment this would be a database write.

---

## Data Honesty Rules (Feb 2026 refactor)

1. **Live feed label** — sidebar always shows 🟢/🟡/⚪ based on actual source
2. **No fake counts** — caregiver page only shows fire counts when real data is loaded
3. **Historical stats always labeled** — all WiDS-derived stats captioned *(WiDS 2021–2025, Real)*
4. **Modeled scenarios clearly marked** — before/after caregiver alert chart labeled as "Modeled Scenario" with FEMA source cited
5. **Graceful degradation** — every page needing large CSVs shows `st.info()` with known aggregate stats when file not deployed

---

## Known Stats (for graceful degradation when CSVs not deployed)

| Metric | Value | Source |
|--------|-------|--------|
| Evacuation Order median duration | 18.5h | WiDS evaczonechangelog (N=3,430) |
| Evacuation Order P90 duration | 120h | WiDS evaczonechangelog |
| Evacuation Warning median | 12.3h | WiDS evaczonechangelog (N=3,966) |
| Evacuation Advisory median | 8.7h | WiDS evaczonechangelog (N=1,618) |
| High-SVI zone clearance | 23.7h median | 28% longer than low-SVI (14.2h) |
| Automated alert channels | ~70% | bots-extra-alerts + bots-alertwest-ai |
| Manual alert channels | ~30% | estimated lag 18–45 min vs 2 min automated |
| External source — WildCAD | 37% | geo_events_externalgeoeventchangelog |

---

## Demo Login Credentials

| Username | Password | Role |
|----------|----------|------|
| dispatcher | fire2025 | Emergency Worker |
| caregiver | evacuate | Caregiver/Evacuee |
| analyst | datathon | Data Analyst |

---

## API Keys & Secrets

- Anthropic model: claude-sonnet-4-6 · Cost: $3/M input, $15/M output tokens
- NASA FIRMS: no API key needed for public CSV endpoints
- Nominatim geocoder: no key, rate-limited, User-Agent header required
- FEMA shelters API: no key needed (public ArcGIS REST endpoint)
- OSRM routing: no key needed (public instance)

---

## Map Layers (command_dashboard_page.py)

| Layer | Color | Toggleable | Notes |
|-------|-------|-----------|-------|
| Base map (CartoDB dark_matter) | Dark | No — always on | Added with control=False so it's not in layer control |
| Fire Perimeters | Orange | Yes | fire_perimeters_approved.geojson — copy to src/ |
| Evacuation Zones | Red | Yes | evac_zones_map.geojson — copy to src/ |
| Live Fire Hotspots | Red/orange circles | Yes | NASA FIRMS, high conf = brighter red |
| Vulnerable Counties | Blue circles | Yes | SVI ≥ threshold, top 300 by SVI score |

---

## Git Workflow

```bash
# Standard push
cd ~/widsdatathon
git add -A
git add -f 01_raw_data/processed/fire_events_with_svi_and_delays.csv
git commit -m "your message"
git push layesh1 main

# If remote has changes you don't have:
git pull layesh1 main --rebase
git push layesh1 main

# Remotes
# layesh1 = https://github.com/layesh1/widsdatathon (your fork, auto-deploys to Streamlit Cloud)
# origin/kleedom = team repo (behind)
```

---

## Known Issues & Gotchas

1. **geo_event_id type mismatch** — changelog stores as "22429.0", geo_events as "22429". Fix: `str(int(float(x)))` with try/except for NaN rows.
2. **Timezone mismatch** — geo_events date_created is timezone-naive, changelog is UTC-aware. Fix: `.dt.tz_localize('UTC')` on fire_start.
3. **fire_events_with_svi_and_delays.csv is gitignored** — use `git add -f` to force-add it.
4. **usfa-registry-national.csv must be in src/** — copy from 01_raw_data/.
5. **GeoJSON files too large for git** — generate locally, copy to src/, never commit.
6. **evac_zones_active.geojson and evac_zones_slim.geojson** — removed from git history on 2026-02-21 via filter-branch. Gitignored. Keep locally only.
7. **secrets.toml was in git history** — removed and gitignored on 2026-02-21. Rotate API key.
8. **Only 653 fires have real evac timing** — WiDS dataset has limited formal activations. 19,392 fires have growth rate data. This is real, not simulated.
9. **fire_prediction_page.py** — call as `render_fire_prediction_page(role=username)` only. Do NOT pass fire_data= or other kwargs. `showstates` is not a valid Plotly geo property — use `showsubunits=True, subunitcolor="#333"` instead.
10. **directions_page.py syntax error line ~1301** — nested f-string quotes. Fix: `f'background:{"#f0f7ff" if is_selected else "#ffffff"};'` (double quotes inside single-quoted f-string). Terminal fix: `python3 -c "path='...src/directions_page.py'; txt=open(path).read(); open(path,'w').write(txt.replace(\"f'background:#{'f0f7ff' if is_selected else 'ffffff'};\'\", 'f\\'background:{\"#f0f7ff\" if is_selected else \"#ffffff\"};\\'')); print('Fixed')"`.
11. **evacuation_planner_page.py** — function signature requires `vulnerable_populations` arg. wildfire_alert_dashboard.py uses `inspect` to detect and pass correct args automatically.
12. **agency_coverage_page.py and alert_channel_equity_page.py** — still in src/ but no longer imported. Replaced by coverage_analysis_page.py. Safe to delete.
13. **Folium map blank** — if map shows blank/grey, the CartoDB tile is not loading. Must use `tiles="CartoDB dark_matter"` as the built-in name. Custom URL tile with `tiles=None` is unreliable across streamlit-folium versions.

---

## External Data

**CDC SVI 2022** — 01_raw_data/external/SVI_2022_US_county.csv
- RPL_THEMES ≥ 0.75 = high vulnerability. Themes: RPL_THEME1–4.
- E_AGE65, E_POV150, E_DISABL, E_NOVEH — component estimates. FIPS = join key.

**Census County Centroids** — wids-caregiver-alert/data/CenPop2020_Mean_CO.txt
- STATEFP (2-digit) + COUNTYFP (3-digit) + LATITUDE + LONGITUDE
- Used with scipy cKDTree for fast nearest-county spatial matching

**NASA FIRMS** — public CSV, no key, fetched at runtime in live_incident_feed.py, TTL=300s

**FEMA Open Shelters** — `https://gis.fema.gov/arcgis/rest/services/NSS/OpenShelters/FeatureServer/0/query` — queried by bounding box around user location, no key needed

**Nominatim geocoder** — `https://nominatim.openstreetmap.org/search` — free, no key, requires User-Agent header

---

## Future Work (Pre-April Conference)
- ✅ Agency coverage gap metric — merged into coverage_analysis_page.py
- ✅ Alert channel equity — merged into coverage_analysis_page.py
- ✅ Live incident feed — live_incident_feed.py, FIRMS public CSV, no key needed
- ✅ ML-based fire spread prediction — fire_prediction_page.py with forward-looking hotspot forecast
- ✅ Data honesty refactor — removed fake demo counts, real data labeled, graceful degradation
- ✅ Evacuee status tracker — dispatcher can track/confirm vulnerable residents in real time
- ✅ Caregiver ↔ dispatcher sync — confirmation on Start Here updates Command Dashboard tracker
- [ ] Zone duration analysis — evac_zones_gis_evaczonechangelog.csv (332MB, not deployed). zone_duration_page.py degrades to known stats. Full analysis requires local run.
- [ ] Fix directions_page.py syntax error permanently
- [ ] Deploy geo_events_geoevent.csv to Streamlit Cloud to enable 🟢 WiDS source (currently runs on FIRMS 🟡)
- [ ] Database backend for evacuee tracker so it persists across sessions
