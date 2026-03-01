"""
data_governance_page.py — 49ers Intelligence Lab · WiDS 2025
Data Governance tab for the Data Analyst role.

Call from wildfire_alert_dashboard.py:
    from data_governance_page import render_data_governance_page
    render_data_governance_page()

Design adapted from the standalone WiDS 2026 Data Governance Dashboard.
All data shown is demo/modelled — replace with live Supabase queries as needed.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta


# ─────────────────────────────────────────────────────────────────────────────
# STYLES  (injected once per page load)
# ─────────────────────────────────────────────────────────────────────────────
_GOV_CSS = """
<style>
/* ── Metric cards ── */
.gov-metric-card {
    padding: 1.2rem 1.4rem;
    border-radius: 10px;
    color: #fff;
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    margin-bottom: 0.4rem;
}
.gov-metric-label { font-size: 0.82rem; opacity: 0.88; margin-bottom: 0.3rem; }
.gov-metric-value { font-size: 2rem; font-weight: 700; line-height: 1.1; }
.gov-metric-delta { font-size: 0.85rem; margin-top: 0.2rem; }

/* ── Alert strips ── */
.gov-alert {
    padding: 0.85rem 1rem;
    border-radius: 6px;
    margin: 0.5rem 0;
    line-height: 1.55;
    font-size: 0.9rem;
}
.gov-critical { background:#fff5f5; border-left:4px solid #e53e3e; }
.gov-warning  { background:#fffbeb; border-left:4px solid #d97706; }
.gov-pass     { background:#f0fdf4; border-left:4px solid #16a34a; }
.gov-info     { background:#eff6ff; border-left:4px solid #3b82f6; }

/* ── Section header ── */
.gov-section-header {
    font-size: 1.05rem;
    font-weight: 600;
    color: #AA0000;
    letter-spacing: 0.02em;
    margin: 1.4rem 0 0.6rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid rgba(170,0,0,0.15);
}

/* ── ERD-style table ── */
.erd-node {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 600;
    margin: 3px;
    border: 1px solid rgba(0,0,0,0.15);
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — coloured metric card
# ─────────────────────────────────────────────────────────────────────────────
def _metric_card(title: str, value: str, delta: str = "", color: str = "#5789b9") -> str:
    delta_html = ""
    if delta:
        delta_color = "#86efac" if delta.startswith("+") else "#fca5a5"
        delta_html = f'<div class="gov-metric-delta" style="color:{delta_color}">{delta}</div>'
    return (
        f'<div class="gov-metric-card" style="background:linear-gradient(135deg,{color} 0%,{color}cc 100%)">'
        f'<div class="gov-metric-label">{title}</div>'
        f'<div class="gov-metric-value">{value}</div>'
        f'{delta_html}</div>'
    )


def _alert(body: str, kind: str = "info") -> None:
    st.markdown(f'<div class="gov-alert gov-{kind}">{body}</div>', unsafe_allow_html=True)


def _section(title: str) -> None:
    st.markdown(f'<div class="gov-section-header">{title}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────
def render_data_governance() -> None:
    st.markdown(_GOV_CSS, unsafe_allow_html=True)

    # ── Page header ───────────────────────────────────────────────────────────
    st.title("Data Governance")
    st.caption(
        "Schema integrity · Quality validation · Pipeline health · Data lineage  "
        "— 49ers Intelligence Lab · WiDS 2025"
    )

    # ── Top-line KPIs ─────────────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(_metric_card("Schema Tables", "7", color="#5789b9"), unsafe_allow_html=True)
    with k2:
        st.markdown(_metric_card("Quality Score", "94.2%", delta="+1.5%", color="#784ea2"), unsafe_allow_html=True)
    with k3:
        st.markdown(_metric_card("Critical Issues", "3", delta="-2 resolved", color="#80aa5e"), unsafe_allow_html=True)

    st.markdown("---")

    # ── Four tabs ─────────────────────────────────────────────────────────────
    tab_schema, tab_quality, tab_pipeline, tab_lineage = st.tabs([
        "Schema & Dictionary",
        "Quality Inspector",
        "Pipeline Status",
        "Data Lineage",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — SCHEMA & DICTIONARY
    # ══════════════════════════════════════════════════════════════════════════
    with tab_schema:
        st.subheader("7-Table Schema Overview")
        st.markdown(
            "All AI/ML training must only use records that meet the approval and "
            "completeness requirements below. Changelog tables provide the full audit "
            "trail required for model provenance."
        )

        # Visual table map
        _section("Entity Map")
        st.markdown("""
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:1rem">
          <span class="erd-node" style="background:#fee2e2;color:#991b1b">geo_events — Core</span>
          <span class="erd-node" style="background:#dcfce7;color:#166534">fire_perimeters — GIS</span>
          <span class="erd-node" style="background:#fef9c3;color:#854d0e">evac_zones — Safety</span>
          <span class="erd-node" style="background:#f1f5f9;color:#475569">regions — Reference</span>
          <span class="erd-node" style="background:#e2e8f0;color:#334155">geoevent_changelog — Audit</span>
          <span class="erd-node" style="background:#e2e8f0;color:#334155">perimeter_changelog — Audit</span>
          <span class="erd-node" style="background:#e2e8f0;color:#334155">evaczone_changelog — Audit</span>
        </div>
        """, unsafe_allow_html=True)

        schema_df = pd.DataFrame([
            {"Table": "geo_events",           "Role": "Core",      "Key Rule": "lat/lng must be non-null for all mapping operations"},
            {"Table": "fire_perimeters",       "Role": "GIS",       "Key Rule": "Only use where approval_status = 'approved'"},
            {"Table": "evac_zones",            "Role": "Safety",    "Key Rule": "status must be Order / Warning / Advisory"},
            {"Table": "regions",               "Role": "Reference", "Key Rule": "Lookup only — do not modify directly"},
            {"Table": "geoevent_changelog",    "Role": "Audit",     "Key Rule": "Use for provenance tracing and model training lineage"},
            {"Table": "perimeter_changelog",   "Role": "Audit",     "Key Rule": "Use for provenance tracing and model training lineage"},
            {"Table": "evaczone_changelog",    "Role": "Audit",     "Key Rule": "Use for provenance tracing and model training lineage"},
        ])
        st.dataframe(schema_df, use_container_width=True, hide_index=True)

        _section("Critical Field Rules")
        f1, f2, f3 = st.tabs(["geo_events", "fire_perimeters", "evac_zones"])
        with f1:
            st.dataframe(pd.DataFrame([
                {"Field": "notification_type",  "Type": "VARCHAR", "Rule": "Must be 'normal' or 'silent'"},
                {"Field": "latitude/longitude", "Type": "NUMERIC", "Rule": "NOT NULL — required for all map operations"},
                {"Field": "is_active",          "Type": "BOOLEAN", "Rule": "If True + is_visible=False → verify notification_type='silent'"},
                {"Field": "is_visible",         "Type": "BOOLEAN", "Rule": "Logical consistency check against is_active"},
            ]), use_container_width=True, hide_index=True)
        with f2:
            st.dataframe(pd.DataFrame([
                {"Field": "approval_status", "Type": "VARCHAR", "Rule": "Filter to 'approved' only before any analysis or training"},
                {"Field": "geo_event_id",    "Type": "INT FK",  "Rule": "NOT NULL — every perimeter must link to a source event"},
                {"Field": "containment",     "Type": "NUMERIC", "Rule": "Percentage: must be in range 0–100"},
            ]), use_container_width=True, hide_index=True)
        with f3:
            st.dataframe(pd.DataFrame([
                {"Field": "status",    "Type": "VARCHAR", "Rule": "Enum: Order / Warning / Advisory only"},
                {"Field": "region_id", "Type": "INT FK",  "Rule": "Must reference a valid row in regions table"},
            ]), use_container_width=True, hide_index=True)

        _alert(
            "<strong>Why this matters:</strong> Using 'pending' or 'rejected' fire perimeters, "
            "or records with missing coordinates, will silently corrupt spatial joins and "
            "model training data. These rules are enforced as quality gates in the pipeline.",
            "info",
        )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — QUALITY INSPECTOR
    # ══════════════════════════════════════════════════════════════════════════
    with tab_quality:
        st.subheader("Automated Validation Results")

        qc1, qc2, qc3 = st.columns(3)
        qc1.metric("Quality Score",   "94.2%", delta="+1.5%")
        qc2.metric("Critical Issues", "3",     delta="-2", delta_color="normal")
        qc3.metric("Warnings",        "8",     delta="+1", delta_color="inverse")

        sev1, sev2, sev3 = st.tabs(["Critical", "Warnings", "Passed"])

        with sev1:
            _alert(
                "<strong>Impossible Containment Values — 3 records</strong><br>"
                "fire_perimeters rows with <code>containment &gt; 100</code>. "
                "Containment is a percentage; valid range is 0–100. "
                "These records are <strong>excluded from model training</strong> until corrected.",
                "critical",
            )
            st.dataframe(pd.DataFrame({
                "Perimeter ID": ["FP-123",    "FP-456",      "FP-789"],
                "Fire Name":    ["Oak Creek",  "Pine Valley", "Cedar Ridge"],
                "Bad Value":    [105,          120,           102],
                "Valid Range":  ["0–100",      "0–100",       "0–100"],
            }), use_container_width=True, hide_index=True)

            _alert(
                "<strong>Orphaned Perimeters — 5 records</strong><br>"
                "fire_perimeters rows missing <code>geo_event_id</code>. "
                "Every perimeter must trace back to a source incident. "
                "These cannot be used in spatial joins or lineage analysis.",
                "critical",
            )
            st.dataframe(pd.DataFrame({
                "Perimeter ID":  ["FP-991",     "FP-992",    "FP-993", "FP-994",    "FP-995"],
                "Source Name":   ["Mystery A",  "Unknown B", "Fire C", "Perimeter D","Zone E"],
                "geo_event_id":  [None,          None,        None,     None,         None],
                "Days Orphaned": [3,             7,           1,        12,           5],
            }), use_container_width=True, hide_index=True)

        with sev2:
            _alert(
                "<strong>Active but Invisible Incidents — 2 records</strong><br>"
                "<code>is_active=True</code> but <code>is_visible=False</code>. "
                "Verify these are intentional 'silent' notification_type events. "
                "If not, this flag combination is logically inconsistent.",
                "warning",
            )
            st.dataframe(pd.DataFrame({
                "Event ID":          ["GE-234",        "GE-567"],
                "Name":              ["Brush Fire",     "Controlled Burn"],
                "is_active":         [True,             True],
                "is_visible":        [False,            False],
                "notification_type": ["silent",         "silent"],
                "Review Needed":     ["Verify intent",  "Expected"],
            }), use_container_width=True, hide_index=True)

            _alert(
                "<strong>Stale Active Incidents — 6 records</strong><br>"
                "Marked <code>is_active=True</code> but no updates in over 72 hours. "
                "Recommend verifying current status with field teams before including in analysis.",
                "warning",
            )

        with sev3:
            _alert("All checks below passed successfully.", "pass")
            st.dataframe(pd.DataFrame({
                "Check": [
                    "Referential Integrity: Regions",
                    "Timestamp Validity",
                    "Duplicate Detection",
                    "Coordinate Range Validation",
                    "Enum Value Compliance",
                    "NULL Constraint Validation",
                ],
                "Records Tested": [1247, 1247, 1247, 1235, 1247, 1247],
                "Pass Rate":      ["100%","100%","100%","99.0%","100%","99.5%"],
                "Status":         ["✅","✅","✅","✅","✅","✅"],
            }), use_container_width=True, hide_index=True)

        _section("Quality Score — 7-Day Trend")
        trend_df = pd.DataFrame({
            "Date":  pd.date_range(end=datetime.now(), periods=7, freq="D"),
            "Score": [92, 91, 93, 94, 93, 95, 94],
            "Critical Issues": [5, 6, 4, 3, 4, 2, 3],
        })
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=trend_df["Date"], y=trend_df["Score"],
            name="Quality Score (%)", line=dict(color="#16a34a", width=2), mode="lines+markers"
        ))
        fig_trend.add_trace(go.Scatter(
            x=trend_df["Date"], y=trend_df["Critical Issues"],
            name="Critical Issues", line=dict(color="#AA0000", width=2, dash="dash"),
            yaxis="y2", mode="lines+markers"
        ))
        fig_trend.update_layout(
            yaxis=dict(title="Quality Score (%)"),
            yaxis2=dict(title="Critical Issues", overlaying="y", side="right"),
            hovermode="x unified", height=320, margin=dict(t=10, b=10),
            legend=dict(orientation="h", y=-0.25),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        _section("Check Distribution")
        check_summary = pd.DataFrame({
            "Severity": ["Critical", "Warning", "Info", "Passed"],
            "Count":    [3, 8, 5, 15],
        })
        fig_bar = px.bar(
            check_summary, x="Severity", y="Count", color="Severity",
            color_discrete_map={"Critical":"#e53e3e","Warning":"#d97706","Info":"#3b82f6","Passed":"#16a34a"},
            height=280,
        )
        fig_bar.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig_bar, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — PIPELINE STATUS
    # ══════════════════════════════════════════════════════════════════════════
    with tab_pipeline:
        st.subheader("Pipeline Health — Last 24 Hours")

        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric("Total Incidents",   "247", delta="+12 today",      delta_color="inverse")
        pc2.metric("Active Fires",      "18",  delta="-3 yesterday")
        pc3.metric("Pending Approvals", "5",   delta="2 urgent",       delta_color="inverse")
        pc4.metric("Quality Score",     "94%", delta="+2%")

        _section("Throughput & Error Rate")
        hours = list(range(24))
        pipe_df = pd.DataFrame({
            "Hour":              hours,
            "Records Processed": [120 + i*5 + (i % 3)*10 for i in hours],
            "Validation Errors": [max(0, 5 - (i % 4)) for i in hours],
            "Approval Lag (min)":[15 + (i % 5)*3 for i in hours],
        })
        fig_pipe = go.Figure()
        fig_pipe.add_trace(go.Scatter(
            x=pipe_df["Hour"], y=pipe_df["Records Processed"],
            name="Records Processed", line=dict(color="#00cc96", width=2)
        ))
        fig_pipe.add_trace(go.Scatter(
            x=pipe_df["Hour"], y=pipe_df["Validation Errors"],
            name="Validation Errors", line=dict(color="#AA0000", width=2, dash="dash")
        ))
        fig_pipe.update_layout(
            xaxis_title="Hour of Day", yaxis_title="Count",
            hovermode="x unified", height=340, margin=dict(t=10, b=10),
        )
        st.plotly_chart(fig_pipe, use_container_width=True)

        _section("Approval Queue")
        _alert(
            "Records with <code>approval_status = 'pending'</code> are excluded from AI training "
            "until reviewed. Update status below and commit to flag them for inclusion.",
            "info",
        )
        approval_df = pd.DataFrame({
            "ID":        ["FP-501",     "FP-502",      "FP-503"],
            "Fire Name": ["Creek Fire", "Bridge Fire", "Valley Fire"],
            "Acres":     [1250,         400,            2100],
            "Containment": ["15%",      "40%",          "5%"],
            "Status":    ["pending",    "pending",      "pending"],
            "Submitted": ["2h ago",     "5h ago",       "1h ago"],
        })
        edited = st.data_editor(
            approval_df,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Approval Status",
                    options=["pending", "approved", "rejected"],
                    required=True,
                ),
                "Acres": st.column_config.NumberColumn("Acres", format="%d ac"),
            },
            hide_index=True, use_container_width=True, key="approval_editor",
        )
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("Commit Approvals", type="primary", key="commit_approvals"):
                st.success("Approval status updated — records queued for pipeline inclusion.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — DATA LINEAGE
    # ══════════════════════════════════════════════════════════════════════════
    with tab_lineage:
        st.subheader("Fire Incident Provenance")
        st.caption(
            "Reconstruct the complete audit trail of any incident from first detection "
            "through containment using the three changelog tables."
        )

        selected = st.selectbox(
            "Select incident for analysis",
            ["Creek Fire (Active)", "Bridge Fire (Contained)", "Oak Fire (Active)"],
            key="lineage_incident_select",
        )

        lc1, lc2, lc3 = st.columns(3)
        lc1.metric("Duration",    "14 hours", delta="ongoing")
        lc2.metric("Acres",       "1,250",    delta="+150 last hour")
        lc3.metric("Containment", "15%",      delta="+5%")

        _section("Data Modification Timeline")
        timeline_df = pd.DataFrame({
            "Event": [
                "Initial Detection", "GeoEvent Created", "First Perimeter",
                "Evac Advisory",     "Perimeter Update", "Evac Warning",
                "Containment Est.",  "Evac Order",
            ],
            "Time": pd.date_range(start="2024-01-15 14:00", periods=8, freq="30min"),
            "Table": [
                "geo_events", "geo_events", "fire_perimeters", "evac_zones",
                "fire_perimeters", "evac_zones", "fire_perimeters", "evac_zones",
            ],
            "Action": ["INSERT","UPDATE","INSERT","INSERT","UPDATE","UPDATE","UPDATE","UPDATE"],
        })
        fig_tl = px.timeline(
            timeline_df,
            x_start="Time",
            x_end=timeline_df["Time"] + timedelta(minutes=28),
            y="Table", color="Action",
            height=300,
            color_discrete_map={"INSERT":"#3b82f6","UPDATE":"#f59e0b"},
        )
        fig_tl.update_layout(margin=dict(t=20, b=10))
        st.plotly_chart(fig_tl, use_container_width=True)

        _section("Subjective Intelligence — Radio Traffic Rate of Spread")
        _alert(
            "Rate-of-spread assessments come from field team radio traffic stored in "
            "<code>geoevent_changelog</code>. These qualitative observations capture "
            "context that satellite sensors miss.",
            "info",
        )
        ros_df = pd.DataFrame({
            "Timestamp":      ["14:00",    "14:15",    "14:45",      "15:20",    "16:00"],
            "Rate of Spread": ["Moderate", "Rapid",    "Rapid",      "Extreme",  "Extreme"],
            "Wind (mph)":     [12,          18,         22,           28,         30],
            "Reporting Team": ["Engine 42", "Engine 42","Battalion 3","Battalion 3","Air Ops"],
        })
        ros_df["Level"] = ros_df["Rate of Spread"].map({"Moderate":1,"Rapid":2,"Extreme":3})

        col_ros, col_tbl = st.columns([2, 1])
        with col_ros:
            fig_ros = px.line(
                ros_df, x="Timestamp", y="Level", markers=True, height=250,
                labels={"Level":"Severity Level"},
            )
            fig_ros.update_layout(
                yaxis=dict(tickmode="array", tickvals=[1,2,3],
                           ticktext=["Moderate","Rapid","Extreme"]),
                margin=dict(t=10, b=10),
            )
            fig_ros.update_traces(line_color="#AA0000", line_width=2,
                                  marker=dict(size=8, color="#AA0000"))
            st.plotly_chart(fig_ros, use_container_width=True)
        with col_tbl:
            st.dataframe(
                ros_df[["Timestamp","Rate of Spread","Wind (mph)","Reporting Team"]],
                use_container_width=True, hide_index=True,
            )

        _alert(
            "<strong>Analysis:</strong> Fire escalated from Moderate → Extreme in under 2 hours, "
            "correlated with wind increase from 12 → 30 mph. "
            "This escalation signature is recommended for inclusion as a high-risk feature "
            "in the predictive model — consider flagging incidents where wind speed doubles "
            "within a 90-minute window.",
            "warning",
        )

        _section("Evacuation Zone Escalation")
        evac_df = pd.DataFrame({
            "Zone":           ["Zone A","Zone A","Zone A","Zone B","Zone B","Zone C"],
            "Time":           ["14:00", "15:30", "16:45", "15:00", "16:30", "16:00"],
            "Status":         ["Advisory","Warning","Order","Advisory","Warning","Advisory"],
            "Households":     [450,       450,      450,    320,      320,      180],
            "Status_Numeric": [1,         2,        3,      1,        2,        1],
        })
        fig_evac = px.line(
            evac_df, x="Time", y="Status_Numeric", color="Zone",
            markers=True, height=280, labels={"Status_Numeric":"Alert Level"},
        )
        fig_evac.update_layout(
            yaxis=dict(tickmode="array", tickvals=[1,2,3],
                       ticktext=["Advisory","Warning","Order"]),
            margin=dict(t=10, b=10),
        )
        st.plotly_chart(fig_evac, use_container_width=True)

        ei1, ei2, ei3 = st.columns(3)
        ei1.metric("Total Households Affected", "950",   delta="3 zones")
        ei2.metric("Mandatory Orders",          "450",   delta="Zone A")
        ei3.metric("Avg. Escalation Time",      "90 min",delta="Advisory → Order")