"""
command_dashboard_page.py — Fixed version
- Base map always visible (no toggle needed)
- GeoJSON layers as proper overlays, not tile layers
- USFA page shows meaningful analysis tied to active fire areas
- Evacuee tracker functional
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path


# ── Data loaders ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_svi_centroids():
    cen_paths = [Path("data/CenPop2020_Mean_CO.txt"),
                 Path("CenPop2020_Mean_CO.txt"),
                 Path("../data/CenPop2020_Mean_CO.txt")]
    svi_paths = [Path("SVI_2022_US_county.csv"),
                 Path("01_raw_data/external/SVI_2022_US_county.csv"),
                 Path("../01_raw_data/external/SVI_2022_US_county.csv")]

    cen_df = None
    for p in cen_paths:
        if p.exists():
            try:
                cen_df = pd.read_csv(p)
                cen_df["FIPS"] = (cen_df["STATEFP"].astype(str).str.zfill(2) +
                                   cen_df["COUNTYFP"].astype(str).str.zfill(3))
                break
            except Exception:
                pass

    svi_df = None
    for p in svi_paths:
        if p.exists():
            try:
                cols = ["FIPS","RPL_THEMES","COUNTY","ST_ABBR","E_AGE65","E_DISABL","E_NOVEH","E_POV150"]
                svi_df = pd.read_csv(p, low_memory=False,
                                      usecols=[c for c in cols])
                svi_df["FIPS"] = svi_df["FIPS"].astype(str).str.zfill(5)
                break
            except Exception:
                pass

    if cen_df is not None and svi_df is not None:
        merged = svi_df.merge(cen_df[["FIPS","LATITUDE","LONGITUDE"]], on="FIPS", how="left")
        return merged.dropna(subset=["LATITUDE","LONGITUDE"])
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def load_usfa():
    for p in [Path("usfa-registry-national.csv"),
               Path("01_raw_data/usfa-registry-national.csv")]:
        if p.exists():
            try:
                return pd.read_csv(p, low_memory=False)
            except Exception:
                pass
    return None


def find_geojson(fname):
    """Try multiple paths to find a GeoJSON file."""
    for p in [Path(fname),
               Path(f"wids-caregiver-alert/src/{fname}"),
               Path(f"src/{fname}"),
               Path(f"../{fname}"),
               Path(f"../src/{fname}")]:
        if p.exists():
            return str(p.resolve())
    return None


# ── Evacuee tracker ───────────────────────────────────────────────────────────

def init_evacuee_tracker():
    if "evacuee_list" not in st.session_state:
        st.session_state.evacuee_list = pd.DataFrame([
            {"name": "Martha Chen",     "address": "142 Oak St, Paradise, CA",      "mobility": "Elderly",         "phone": "530-555-0101", "status": "Unconfirmed"},
            {"name": "Robert Okafor",   "address": "77 Pine Ridge Rd, Magalia, CA", "mobility": "Disabled",        "phone": "530-555-0144", "status": "Unconfirmed"},
            {"name": "Delores Perez",   "address": "89 Skyway, Paradise, CA",       "mobility": "Elderly",         "phone": "530-555-0199", "status": "Unconfirmed"},
            {"name": "James Whitmore",  "address": "312 Pentz Rd, Paradise, CA",    "mobility": "No vehicle",      "phone": "530-555-0177", "status": "Unconfirmed"},
            {"name": "Yuki Tanaka",     "address": "55 Bille Rd, Paradise, CA",     "mobility": "Disabled",        "phone": "530-555-0155", "status": "Evacuated ✅"},
            {"name": "Gloria Martinez", "address": "201 Clark Rd, Chico, CA",       "mobility": "Medical equip.",  "phone": "530-555-0188", "status": "Unconfirmed"},
        ])


# ── Main render ───────────────────────────────────────────────────────────────

def render_command_dashboard(fire_data, fire_source, fire_label):
    st.title("⚡ Command Dashboard")
    st.caption(f"Emergency Worker View · {fire_label} · WiDS 2021–2025 Historical Benchmarks")

    init_evacuee_tracker()

    # Historical benchmarks
    st.subheader("📊 Historical Response Benchmarks  *(WiDS 2021–2025, Real Data)*")
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Median Time to Evac Order", "1.1h",
              help="653 fires with confirmed evac actions")
    h2.metric("Worst-Case (90th %ile)", "32h",
              help="1 in 10 fires takes >32h for an official order")
    h3.metric("Fires Exceeding 6h Delay", "20%",
              delta="Critical window", delta_color="inverse")
    h4.metric("Vuln County Growth Rate", "11.7 ac/hr",
              delta="+17% vs non-vuln", delta_color="inverse")

    st.divider()

    tab_map, tab_evacuees, tab_resources = st.tabs([
        "🗺️ Active Fire Map", "👥 Evacuee Status Tracker", "🚒 Fire Dept Resources"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: MAP — always visible, GeoJSON as proper overlays
    # ══════════════════════════════════════════════════════════════════════════
    with tab_map:
        col1, col2, col3 = st.columns([1,1,2])
        with col1:
            state_filter = st.selectbox("Filter by State", [
                "All","CA","OR","WA","CO","NM","AZ","TX","MT","ID","NV",
                "FL","GA","NC","SC","LA","OK","KS","NE"])
        with col2:
            svi_min = st.slider("Show counties w/ SVI ≥", 0.5, 1.0, 0.75, 0.05)
        with col3:
            show_perimeters  = st.checkbox("Fire perimeters (GeoJSON)", value=True)
            show_evac_zones  = st.checkbox("Evacuation zones (GeoJSON)", value=True)

        # ── Build map — dark base tile hardcoded, always on ──────────────────
        m = folium.Map(
            location=[39.5, -98.5],
            zoom_start=4,
            tiles=None   # base tile added manually below with control=False
        )

        # Base tile always on, not in layer control, renamed clearly
        folium.TileLayer(
            "CartoDB dark_matter",
            name="Base Map",
            control=False,
            overlay=False
        ).add_to(m)

        # ── GeoJSON: fire perimeters ──────────────────────────────────────────
        perim_path = find_geojson("fire_perimeters_approved.geojson")
        if show_perimeters and perim_path:
            try:
                folium.GeoJson(
                    perim_path,
                    name="🔶 Fire Perimeters",
                    style_function=lambda f: {
                        "fillColor": "#FF6600",
                        "color":     "#FF4400",
                        "weight":    2,
                        "fillOpacity": 0.40
                    },
                    show=True
                ).add_to(m)
            except Exception as e:
                st.warning(f"Fire perimeters GeoJSON error: {e}")
        elif show_perimeters:
            st.caption("⚠️ `fire_perimeters_approved.geojson` not found in src/. "
                       "Copy from `01_raw_data/processed/` to `wids-caregiver-alert/src/`.")

        # ── GeoJSON: evac zones ───────────────────────────────────────────────
        evac_path = find_geojson("evac_zones_map.geojson")
        if show_evac_zones and evac_path:
            try:
                folium.GeoJson(
                    evac_path,
                    name="🔴 Evacuation Zones",
                    style_function=lambda f: {
                        "fillColor": "#FF2200",
                        "color":     "#CC0000",
                        "weight":    1.5,
                        "fillOpacity": 0.30
                    },
                    show=True
                ).add_to(m)
            except Exception as e:
                st.warning(f"Evac zones GeoJSON error: {e}")
        elif show_evac_zones:
            st.caption("⚠️ `evac_zones_map.geojson` not found in src/. "
                       "Copy from `01_raw_data/processed/` to `wids-caregiver-alert/src/`.")

        # ── Live FIRMS fire hotspots ──────────────────────────────────────────
        n_plotted = 0
        if fire_source != "none" and len(fire_data) > 0:
            plot_df = fire_data.copy()
            if state_filter != "All" and "state" in plot_df.columns:
                plot_df = plot_df[plot_df["state"] == state_filter]

            fire_layer = folium.FeatureGroup(name="🔥 Live Fire Hotspots", show=True)
            for _, row in plot_df.head(500).iterrows():
                try:
                    conf     = str(row.get("confidence",""))
                    is_high  = conf.lower() in ["h","high","n","nominal"] or \
                               (conf.isdigit() and int(conf) >= 80)
                    color    = "#FF2200" if is_high else "#FF8800"
                    radius   = 6 if is_high else 4
                    folium.CircleMarker(
                        location=[float(row["lat"]), float(row["lon"])],
                        radius=radius,
                        color=color, fill=True, fill_color=color, fill_opacity=0.75,
                        tooltip=f"🔥 FIRMS hotspot · conf: {conf}"
                    ).add_to(fire_layer)
                    n_plotted += 1
                except Exception:
                    pass
            fire_layer.add_to(m)

        # ── Vulnerable counties ───────────────────────────────────────────────
        svi_df = load_svi_centroids()
        if svi_df is not None:
            vul_layer = folium.FeatureGroup(name="🔵 Vulnerable Counties (SVI)", show=True)
            filtered  = svi_df[svi_df["RPL_THEMES"] >= svi_min]
            if state_filter != "All" and "ST_ABBR" in filtered.columns:
                filtered = filtered[filtered["ST_ABBR"] == state_filter]
            for _, row in filtered.nlargest(300, "RPL_THEMES").iterrows():
                try:
                    folium.CircleMarker(
                        location=[row["LATITUDE"], row["LONGITUDE"]],
                        radius=8,
                        color="#4a90d9", fill=True, fill_color="#4a90d9", fill_opacity=0.35,
                        tooltip=(f"{row.get('COUNTY','County')}, {row.get('ST_ABBR','')} "
                                 f"· SVI {row['RPL_THEMES']:.2f}")
                    ).add_to(vul_layer)
                except Exception:
                    pass
            vul_layer.add_to(m)

        # ── Layer control ─────────────────────────────────────────────────────
        folium.LayerControl(collapsed=False).add_to(m)

        # ── HTML legend ───────────────────────────────────────────────────────
        legend = """
        <div style="position:fixed;bottom:24px;left:24px;z-index:9999;
                    background:rgba(15,15,15,0.92);padding:10px 14px;
                    border-radius:8px;font-size:12px;color:#eee;
                    border:1px solid #444;line-height:1.8;">
            <b style="font-size:13px;">Map Legend</b><br>
            <span style="color:#FF2200;font-size:16px;">●</span> High-confidence fire (FIRMS)<br>
            <span style="color:#FF8800;font-size:16px;">●</span> Moderate fire hotspot<br>
            <span style="color:#4a90d9;font-size:16px;">●</span> Vulnerable county (SVI ≥ threshold)<br>
            <span style="color:#FF6600;font-size:16px;">▬</span> Fire perimeter (NIFC)<br>
            <span style="color:#FF2200;font-size:16px;">▬</span> Evacuation zone
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend))

        st_folium(m, width="100%", height=560, returned_objects=[])

        # Status caption
        if fire_source == "none":
            st.caption("⚪ No live fire data. Showing vulnerable county locations only.")
        else:
            st.caption(
                f"{fire_label} · **{n_plotted} hotspots** plotted · "
                f"Blue circles = SVI ≥ {svi_min} counties · "
                f"GeoJSON layers: {'✅ loaded' if (perim_path or evac_path) else '⚠️ not found — copy to src/'}"
            )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: EVACUEE TRACKER
    # ══════════════════════════════════════════════════════════════════════════
    with tab_evacuees:
        st.subheader("👥 Vulnerable Resident Evacuation Tracker")
        st.markdown(
            "Track whether high-risk individuals in active evacuation zones have been "
            "confirmed evacuated. Field teams update status as they make contact. "
            "When a caregiver confirms on the **Start Here** page, status updates here automatically."
        )

        df = st.session_state.evacuee_list.copy()
        total     = len(df)
        evacuated = (df["status"] == "Evacuated ✅").sum()
        unconf    = total - evacuated

        k1, k2, k3 = st.columns(3)
        k1.metric("Total Tracked", total)
        k2.metric("Confirmed Evacuated", evacuated,
                  delta=f"{evacuated/total*100:.0f}% of tracked",
                  delta_color="normal")
        k3.metric("⚠️ Still Unconfirmed", unconf,
                  delta="Needs contact" if unconf > 0 else "All accounted for",
                  delta_color="inverse" if unconf > 0 else "normal")

        # Progress bar
        st.progress(evacuated / total if total > 0 else 0,
                    text=f"{evacuated}/{total} residents accounted for")

        st.divider()

        # Per-resident rows
        for i, row in st.session_state.evacuee_list.iterrows():
            col_info, col_mob, col_stat, col_btn = st.columns([3, 1.5, 1.5, 1.5])
            with col_info:
                st.markdown(f"**{row['name']}**  \n"
                            f"<span style='color:#888;font-size:0.8rem'>{row['address']}</span>  \n"
                            f"<span style='color:#888;font-size:0.8rem'>📞 {row['phone']}</span>",
                            unsafe_allow_html=True)
            with col_mob:
                mob_colors = {"Elderly":"#FFC107","Disabled":"#FF9800",
                              "No vehicle":"#4a90d9","Medical equip.":"#9b59b6"}
                color = mob_colors.get(row["mobility"], "#888")
                st.markdown(f"<span style='color:{color};font-size:0.85rem'>⚑ {row['mobility']}</span>",
                            unsafe_allow_html=True)
            with col_stat:
                if row["status"] == "Evacuated ✅":
                    st.success("Evacuated ✅", icon=None)
                else:
                    st.warning("Unconfirmed ⚠️", icon=None)
            with col_btn:
                if row["status"] != "Evacuated ✅":
                    if st.button("✅ Confirm", key=f"conf_{i}", use_container_width=True):
                        st.session_state.evacuee_list.at[i, "status"] = "Evacuated ✅"
                        st.rerun()
                else:
                    if st.button("↩️ Undo", key=f"undo_{i}", use_container_width=True):
                        st.session_state.evacuee_list.at[i, "status"] = "Unconfirmed"
                        st.rerun()

        st.divider()
        with st.expander("➕ Add resident to tracker"):
            c1, c2, c3, c4 = st.columns(4)
            new_name  = c1.text_input("Name")
            new_addr  = c2.text_input("Address")
            new_mob   = c3.selectbox("Mobility need",
                                      ["Elderly","Disabled","No vehicle","Medical equip.","Other"])
            new_phone = c4.text_input("Phone")
            if st.button("Add to tracker") and new_name and new_addr:
                new_row = pd.DataFrame([{"name": new_name, "address": new_addr,
                                          "mobility": new_mob, "phone": new_phone,
                                          "status": "Unconfirmed"}])
                st.session_state.evacuee_list = pd.concat(
                    [st.session_state.evacuee_list, new_row], ignore_index=True)
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: FIRE DEPT RESOURCES — made meaningful
    # ══════════════════════════════════════════════════════════════════════════
    with tab_resources:
        st.subheader("🚒 Fire Department Resources — USFA National Registry")
        st.markdown(
            "Use this to assess **resource gaps** near active fire zones. "
            "Counties with high SVI but low career firefighter counts are most at risk "
            "of under-resourced evacuations."
        )

        usfa_df = load_usfa()
        if usfa_df is None:
            st.error("⚠️ `usfa-registry-national.csv` not found. "
                     "Copy from `01_raw_data/` to `wids-caregiver-alert/src/`.")
            return

        # Normalize columns
        usfa_df.columns = [c.lower().strip().replace(" ","_") for c in usfa_df.columns]

        # Find key columns
        state_col   = next((c for c in usfa_df.columns if "state" in c and "hq" in c), None) or \
                      next((c for c in usfa_df.columns if c in ["state","hq_state"]), None)
        county_col  = next((c for c in usfa_df.columns if "county" in c), None)
        name_col    = next((c for c in usfa_df.columns if "name" in c or "fd_name" in c), None)
        type_col    = next((c for c in usfa_df.columns if "type" in c and "dept" in c), None) or \
                      next((c for c in usfa_df.columns if "type" in c), None)
        career_col  = next((c for c in usfa_df.columns if "career" in c), None)
        vol_col     = next((c for c in usfa_df.columns if "volunt" in c and "ff" in c.lower()), None) or \
                      next((c for c in usfa_df.columns if "volunt" in c), None)
        station_col = next((c for c in usfa_df.columns if "station" in c), None)

        # ── Filters ──────────────────────────────────────────────────────────
        fc1, fc2 = st.columns(2)
        with fc1:
            all_states = sorted(usfa_df[state_col].dropna().unique()) if state_col else []
            # Default to CA if available — most fire-relevant
            default_idx = all_states.index("CA") + 1 if "CA" in all_states else 0
            sel_state = st.selectbox("Filter by State", ["All"] + all_states,
                                      index=default_idx, key="usfa_state")
        with fc2:
            if type_col:
                all_types = ["All"] + sorted(usfa_df[type_col].dropna().unique().tolist())
                sel_type  = st.selectbox("Department Type", all_types, key="usfa_type")
            else:
                sel_type = "All"

        fdf = usfa_df.copy()
        if sel_state != "All" and state_col:
            fdf = fdf[fdf[state_col] == sel_state]
        if sel_type != "All" and type_col:
            fdf = fdf[fdf[type_col] == sel_type]

        # ── KPIs ─────────────────────────────────────────────────────────────
        st.caption(f"Showing **{len(fdf):,}** of {len(usfa_df):,} departments")
        u1, u2, u3, u4 = st.columns(4)
        u1.metric("Departments",       f"{len(fdf):,}")
        u2.metric("Total Stations",    f"{pd.to_numeric(fdf[station_col], errors='coerce').sum():,.0f}" if station_col else "—")
        u3.metric("Career FF",         f"{pd.to_numeric(fdf[career_col],  errors='coerce').sum():,.0f}" if career_col  else "—")
        u4.metric("Volunteer FF",      f"{pd.to_numeric(fdf[vol_col],     errors='coerce').sum():,.0f}" if vol_col     else "—")

        st.divider()

        # ── Meaningful analysis: resource gap by county ───────────────────────
        if sel_state != "All" and county_col and career_col:
            st.markdown("#### 🔍 Resource Gap Analysis — Which Counties Are Under-Resourced?")
            st.markdown(
                "Counties with **high SVI** (vulnerable population) but **low career firefighter count** "
                "face the greatest risk of inadequate emergency response during wildfires."
            )

            # Aggregate USFA by county
            fdf["career_n"] = pd.to_numeric(fdf[career_col], errors="coerce").fillna(0)
            county_resources = fdf.groupby(county_col).agg(
                total_depts=   (name_col,    "count"),
                career_ff=     ("career_n",  "sum"),
            ).reset_index()
            county_resources.columns = ["County", "Departments", "Career FF"]

            # Join with SVI if available
            svi_df = load_svi_centroids()
            if svi_df is not None and "ST_ABBR" in svi_df.columns:
                state_svi = svi_df[svi_df["ST_ABBR"] == sel_state][
                    ["COUNTY","RPL_THEMES","E_AGE65","E_DISABL","E_NOVEH"]
                ].copy()
                state_svi.columns = ["County","SVI Score","Elderly (65+)","Disabled","No Vehicle"]
                # Fuzzy match on county name
                state_svi["County_key"] = state_svi["County"].str.upper().str.replace(" COUNTY","").str.strip()
                county_resources["County_key"] = county_resources["County"].str.upper().str.strip()
                merged = county_resources.merge(state_svi, on="County_key", how="left", suffixes=("","_svi"))
                merged = merged.drop(columns=["County_key","County_svi"], errors="ignore")

                if "SVI Score" in merged.columns:
                    # Compute gap score: high SVI + low career FF = high gap
                    max_ff = merged["Career FF"].replace(0, np.nan).max()
                    merged["Resource Gap Score"] = (
                        merged["SVI Score"].fillna(0) * 0.6 +
                        (1 - (merged["Career FF"] / max_ff).fillna(0)) * 0.4
                    ).round(2)

                    merged = merged.sort_values("Resource Gap Score", ascending=False)

                    # Highlight chart
                    fig = px.scatter(
                        merged.dropna(subset=["SVI Score"]).head(40),
                        x="Career FF", y="SVI Score",
                        size="Departments",
                        color="Resource Gap Score",
                        color_continuous_scale=["#4CAF50","#FFC107","#FF4444"],
                        hover_name="County",
                        hover_data={"Departments": True, "Career FF": True,
                                    "SVI Score": ":.2f", "Resource Gap Score": ":.2f"},
                        title=f"Resource Gap: Career FF vs SVI Score — {sel_state} Counties",
                        labels={"Career FF": "Career Firefighters", "SVI Score": "SVI Score (vulnerability)"}
                    )
                    fig.update_layout(
                        template="plotly_dark", height=400,
                        margin=dict(l=40,r=10,t=40,b=40)
                    )
                    # Annotation for high-gap quadrant
                    fig.add_annotation(
                        x=merged["Career FF"].quantile(0.1),
                        y=0.85,
                        text="⚠️ High vulnerability,<br>low resources",
                        showarrow=False,
                        font=dict(color="#FF4444", size=12)
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Top gap counties table
                    st.markdown("**Top 10 Counties by Resource Gap Score**")
                    display_cols = [c for c in ["County","SVI Score","Career FF","Departments",
                                                 "Elderly (65+)","Disabled","No Vehicle",
                                                 "Resource Gap Score"] if c in merged.columns]
                    st.dataframe(
                        merged[display_cols].head(10).round(2),
                        use_container_width=True, hide_index=True
                    )
                    st.caption(
                        "Resource Gap Score = 0.6 × SVI + 0.4 × (1 − career_FF_fraction). "
                        "Score closer to 1.0 = highest need for additional resources / caregiver alerts."
                    )

        st.divider()

        # ── Department type breakdown ─────────────────────────────────────────
        if type_col and len(fdf) > 0:
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                type_counts = fdf[type_col].value_counts().head(6)
                fig_t = go.Figure(go.Bar(
                    x=type_counts.index, y=type_counts.values,
                    marker_color="#FF6347",
                    text=type_counts.values, textposition="outside"
                ))
                fig_t.update_layout(
                    template="plotly_dark", title="Departments by Type",
                    height=280, margin=dict(l=20,r=10,t=40,b=60),
                    xaxis_tickangle=-20, yaxis_title="Count"
                )
                st.plotly_chart(fig_t, use_container_width=True)

            with col_chart2:
                # Volunteer vs career ratio — key for wildfire response capacity
                if career_col and vol_col:
                    career_total = pd.to_numeric(fdf[career_col], errors="coerce").sum()
                    vol_total    = pd.to_numeric(fdf[vol_col],    errors="coerce").sum()
                    if career_total + vol_total > 0:
                        fig_v = go.Figure(go.Pie(
                            labels=["Career FF", "Volunteer FF"],
                            values=[career_total, vol_total],
                            marker_colors=["#FF6347","#4a90d9"],
                            textinfo="label+percent"
                        ))
                        fig_v.update_layout(
                            template="plotly_dark",
                            title=f"FF Composition — {sel_state if sel_state != 'All' else 'National'}",
                            height=280, margin=dict(l=20,r=20,t=40,b=20)
                        )
                        st.plotly_chart(fig_v, use_container_width=True)

        # ── Raw table ─────────────────────────────────────────────────────────
        with st.expander("📋 Full Department List"):
            disp_cols = [c for c in [name_col, "hq_city", state_col, county_col,
                                      type_col, station_col] if c]
            rename_map = {name_col: "Department", "hq_city": "City", state_col: "State",
                          county_col: "County", type_col: "Type", station_col: "Stations"}
            st.dataframe(
                fdf[disp_cols].head(200).rename(columns=rename_map),
                use_container_width=True, hide_index=True
            )
            st.caption(f"Showing top 200 of {len(fdf):,}. Use filters above to narrow down.")
