"""
caregiver_start_page.py
Caregiver / Evacuee landing page.
Real workflow:
  1. Enter your address/location
  2. System checks NASA FIRMS for fires within X miles (real data)
  3. If fire detected → auto-show nearest shelter + evacuation route
  4. If no fire → show risk profile and preparation checklist
  5. Caregiver confirms evacuation → saved to Supabase + change log
  6. Dispatcher tracker updated in real time
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import folium
from streamlit_folium import st_folium
from io import StringIO
from pathlib import Path
from datetime import datetime, timezone

FIRMS_VIIRS = (
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/"
    "suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv"
)
OVERPASS_URL     = "https://overpass-api.de/api/interpreter"
FEMA_SHELTERS_URL = (
    "https://gis.fema.gov/arcgis/rest/services/NSS/OpenShelters/FeatureServer/0/query"
)


# ── Supabase helpers ───────────────────────────────────────────────────────────
def _get_sb():
    """Return Supabase client or None."""
    try:
        from supabase import create_client
        return create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_ANON_KEY"],
        )
    except Exception:
        return None


def save_evacuation_status(record: dict) -> bool:
    """
    Upsert an evacuation record keyed on (username, resident_name).
    record keys: username, resident_name, resident_address,
                 evacuated_to, status, lat, lon, reported_by,
                 verified_by, verification_method, notes
    Returns True on success.
    """
    sb = _get_sb()
    if not sb:
        return False
    try:
        sb.table("evacuation_status").upsert(
            {
                **record,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="username,resident_name",
        ).execute()
        return True
    except Exception as e:
        st.warning(f"Could not save to database: {e}")
        return False


def log_evacuation_change(
    username: str,
    resident_name: str,
    old_status: str,
    new_status: str,
    changed_by: str = "",
    verified_by: str = "",
    verification_method: str = "",
    note: str = "",
) -> None:
    """
    Append a row to evacuation_changelog — never overwrites, always appends.
    changed_by  : username of whoever triggered the change
    verified_by : username of the dispatcher/worker who verified (if any)
    verification_method: 'access_code' | 'dispatcher_confirm' | 'self_reported'
    """
    sb = _get_sb()
    if not sb:
        return
    try:
        sb.table("evacuation_changelog").insert({
            "username":            username,
            "resident_name":       resident_name,
            "old_status":          old_status,
            "new_status":          new_status,
            "changed_by":          changed_by or username,
            "verified_by":         verified_by,
            "verification_method": verification_method,
            "note":                note,
            "changed_at":          datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass


def get_evacuation_record(username: str, resident_name: str) -> dict | None:
    """Fetch the latest evacuation record for this user + resident."""
    sb = _get_sb()
    if not sb:
        return None
    try:
        result = (
            sb.table("evacuation_status")
            .select("*")
            .eq("username", username)
            .ilike("resident_name", resident_name)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


def get_my_evacuees(username: str) -> list[dict]:
    """All evacuation records this caregiver has submitted."""
    sb = _get_sb()
    if not sb:
        return []
    try:
        result = (
            sb.table("evacuation_status")
            .select("*")
            .eq("username", username)
            .order("updated_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def get_changelog(username: str, resident_name: str = None, limit: int = 20) -> list[dict]:
    """Fetch change log entries, optionally filtered by resident."""
    sb = _get_sb()
    if not sb:
        return []
    try:
        q = (
            sb.table("evacuation_changelog")
            .select("*")
            .eq("username", username)
            .order("changed_at", desc=True)
            .limit(limit)
        )
        if resident_name:
            q = q.ilike("resident_name", resident_name)
        return q.execute().data or []
    except Exception:
        return []


# ── Geo / API helpers ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_firms_us():
    try:
        r = requests.get(FIRMS_VIIRS, timeout=12)
        if r.status_code == 200 and len(r.text) > 200:
            df = pd.read_csv(StringIO(r.text))
            df.columns = [c.lower() for c in df.columns]
            df["lat"] = pd.to_numeric(df.get("latitude", df.get("lat")), errors="coerce")
            df["lon"] = pd.to_numeric(df.get("longitude", df.get("lon")), errors="coerce")
            df = df.dropna(subset=["lat", "lon"])
            return df[(df["lat"].between(24, 50)) & (df["lon"].between(-125, -65))]
    except Exception:
        pass
    return None


@st.cache_data(ttl=600, show_spinner=False)
def get_fema_shelters(lat, lon, radius_km=80):
    try:
        deg = radius_km / 111
        params = {
            "where":         "SHELTER_STATUS='Open'",
            "geometry":      f"{lon-deg},{lat-deg},{lon+deg},{lat+deg}",
            "geometryType":  "esriGeometryEnvelope",
            "spatialRel":    "esriSpatialRelIntersects",
            "outFields":     "SHELTER_NAME,ADDRESS,CITY,STATE,CAPACITY,LATITUDE,LONGITUDE,PHONE",
            "returnGeometry":"false",
            "f":             "json",
            "resultRecordCount": 10,
        }
        r = requests.get(FEMA_SHELTERS_URL, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "features" in data and len(data["features"]) > 0:
                return pd.DataFrame([f["attributes"] for f in data["features"]])
    except Exception:
        pass
    return None


def geocode_address(address):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "WiDS-WildfireAlertSystem/1.0"},
            timeout=8,
        )
        results = r.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"]), results[0]["display_name"]
    except Exception:
        pass
    return None, None, None


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(a))


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d %Y, %H:%M UTC")
    except Exception:
        return iso


def _save_simple_status(username, new_status, old_status, lat, lon, address, note):
    """Save a simple evacuated/not-evacuated status and log the change."""
    record = {
        "username":         username,
        "resident_name":    username,   # for self-reporting, resident = the user themselves
        "resident_address": address,
        "evacuated_to":     "",
        "status":           new_status,
        "lat":              lat,
        "lon":              lon,
        "reported_by":      username,
        "notes":            note,
    }
    ok = save_evacuation_status(record)
    if ok:
        log_evacuation_change(
            username=username,
            resident_name=username,
            old_status=old_status or "Not recorded",
            new_status=new_status,
            note=note,
        )
        if "evacuee_list" in st.session_state:
            mask = st.session_state.evacuee_list["name"].str.lower() == username.lower()
            if mask.any():
                st.session_state.evacuee_list.loc[mask, "status"] = (
                    "Evacuated ✅" if new_status == "Evacuated" else new_status
                )
    else:
        st.warning("Status saved to session only — database unavailable.")


# ── Main page ──────────────────────────────────────────────────────────────────
def render_caregiver_start_page():
    username = st.session_state.get("username", "guest")

    st.title("Wildfire Evacuation Support")
    st.markdown(
        "Use this page to check fire activity near your location, find open shelters, "
        "and confirm when someone in your care has evacuated safely."
    )

    # Risk callout — brief, plain language
    st.warning(
        "Fires in high-risk areas grow **17% faster** and the average time to an "
        "official evacuation order is only **1.1 hours**. Don't wait for the order — "
        "if there's fire nearby, start moving.",
        icon="⚠️",
    )

    st.divider()

    # ── 1. Location check ─────────────────────────────────────────────────────
    st.subheader("Enter Location to Monitor")
    col_addr, col_radius = st.columns([3, 1])
    with col_addr:
        address_input = st.text_input(
            "Address or city",
            placeholder="e.g. 142 Oak St, Paradise, CA",
            help="Used only to check for nearby fires. Not stored.",
        )
    with col_radius:
        search_radius = st.selectbox(
            "Search radius",
            [10, 25, 50, 100],
            index=1,
            format_func=lambda x: f"{x} miles",
        )

    if st.button("Check Fire Risk Near Me", type="primary", disabled=not address_input):
        with st.spinner("Locating address…"):
            user_lat, user_lon, display_name = geocode_address(address_input)

        if user_lat is None:
            st.error("Couldn't find that address. Try including city and state.")
            return

        st.success(f"Found: {display_name}")
        st.session_state["user_lat"]  = user_lat
        st.session_state["user_lon"]  = user_lon
        st.session_state["user_addr"] = display_name

        with st.spinner("Checking NASA FIRMS satellite data…"):
            firms_df = get_firms_us()

        if firms_df is not None and len(firms_df) > 0:
            firms_df["dist_km"] = firms_df.apply(
                lambda r: haversine_km(user_lat, user_lon, r["lat"], r["lon"]), axis=1
            )
            radius_km = search_radius * 1.609
            nearby = firms_df[firms_df["dist_km"] <= radius_km].sort_values("dist_km")
            st.session_state["nearby_fires"] = nearby
            st.session_state["firms_loaded"] = True
        else:
            st.session_state["nearby_fires"] = pd.DataFrame()
            st.session_state["firms_loaded"] = False

    # ── 2. Results ────────────────────────────────────────────────────────────
    if "user_lat" in st.session_state:
        user_lat = st.session_state["user_lat"]
        user_lon = st.session_state["user_lon"]
        nearby   = st.session_state.get("nearby_fires", pd.DataFrame())
        firms_ok = st.session_state.get("firms_loaded", False)

        st.divider()

        if not firms_ok:
            st.warning(
                "NASA FIRMS data unavailable right now. "
                "Check [Ready.gov](https://www.ready.gov) or "
                "[CAL FIRE](https://www.fire.ca.gov/incidents/) for current orders."
            )
        elif len(nearby) == 0:
            st.success(
                f"No active fire hotspots detected within {search_radius} miles "
                "in the last 24 hours (NASA FIRMS VIIRS)."
            )
        else:
            closest_mi = nearby.iloc[0]["dist_km"] / 1.609
            n_fires    = len(nearby)
            if closest_mi < 5:
                st.error(
                    f"**IMMEDIATE DANGER** — {n_fires} hotspot(s) detected, "
                    f"closest is **{closest_mi:.1f} miles** away. Evacuate now."
                )
            elif closest_mi < 20:
                st.warning(
                    f"Fire activity {closest_mi:.1f} miles away — "
                    f"{n_fires} hotspot(s) within {search_radius} miles. "
                    "Be ready to leave immediately."
                )
            else:
                st.info(f"Fire activity detected, closest hotspot is {closest_mi:.1f} miles away. Monitor conditions.")

        # Map
        m = folium.Map(location=[user_lat, user_lon], zoom_start=9, tiles="CartoDB dark_matter")
        folium.Marker(
            [user_lat, user_lon],
            popup="Your location",
            icon=folium.Icon(color="blue", icon="home", prefix="fa"),
        ).add_to(m)

        for _, row in nearby.head(50).iterrows():
            try:
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=6,
                    color="#FF2200", fill=True, fill_color="#FF2200", fill_opacity=0.7,
                    tooltip=f"Fire — {row['dist_km']:.1f} km away",
                ).add_to(m)
            except Exception:
                pass

        # Shelters
        with st.spinner("Searching for open shelters…"):
            shelters = get_fema_shelters(user_lat, user_lon, search_radius * 1.609)

        if shelters is not None and len(shelters) > 0:
            for _, s in shelters.iterrows():
                try:
                    slat, slon = float(s.get("LATITUDE", 0)), float(s.get("LONGITUDE", 0))
                    if slat and slon:
                        folium.Marker(
                            [slat, slon],
                            popup=folium.Popup(
                                f"<b>{s.get('SHELTER_NAME','Shelter')}</b><br>"
                                f"{s.get('ADDRESS','')}, {s.get('CITY','')}<br>"
                                f"Capacity: {s.get('CAPACITY','—')}<br>"
                                f"Phone: {s.get('PHONE','—')}",
                                max_width=200,
                            ),
                            icon=folium.Icon(color="green", icon="plus-sign", prefix="glyphicon"),
                        ).add_to(m)
                except Exception:
                    pass

        st_folium(m, width="100%", height=420, returned_objects=[])

        # Shelter table
        st.subheader("Open Shelters Near You")
        if shelters is not None and len(shelters) > 0:
            cols = [c for c in ["SHELTER_NAME","ADDRESS","CITY","STATE","CAPACITY","PHONE"]
                    if c in shelters.columns]
            st.dataframe(
                shelters[cols].rename(columns={
                    "SHELTER_NAME": "Shelter", "ADDRESS": "Address", "CITY": "City",
                    "STATE": "State", "CAPACITY": "Capacity", "PHONE": "Phone",
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("Source: FEMA National Shelter System (live)")
        else:
            st.info(
                "No FEMA open shelters found for this area. "
                "Call 2-1-1 or check [ARC shelter finder]"
                "(https://www.redcross.org/get-help/disaster-relief-and-recovery-services/find-an-open-shelter.html)."
            )

        st.divider()

        # ── 3. Evacuation status ───────────────────────────────────────────────
        st.subheader("Update Your Evacuation Status")
        st.markdown(
            "Let emergency workers know whether you have evacuated. "
            "This updates the dispatcher's tracker in real time."
        )

        # Show current status if already recorded
        existing_self = get_evacuation_record(username, username)
        current_status = existing_self["status"] if existing_self else None

        if current_status == "Evacuated":
            st.success("Your current status: **Evacuated** ✅")
        elif current_status == "Not Evacuated":
            st.error("Your current status: **Not Evacuated** — emergency workers may follow up.")
        else:
            st.info("Your evacuation status has not been recorded yet.")

        confirm_note = st.text_input(
            "Optional note",
            placeholder="Where you evacuated to, special needs, contact info…",
        )

        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("I have evacuated", type="primary", use_container_width=True):
                _save_simple_status(
                    username, "Evacuated", current_status,
                    user_lat, user_lon,
                    st.session_state.get("user_addr", ""),
                    confirm_note.strip(),
                )
                st.rerun()
        with col_no:
            if st.button("I have NOT evacuated", use_container_width=True):
                _save_simple_status(
                    username, "Not Evacuated", current_status,
                    user_lat, user_lon,
                    st.session_state.get("user_addr", ""),
                    confirm_note.strip(),
                )
                st.rerun()

    st.divider()

    # ── 4. My status history ───────────────────────────────────────────────────
    st.subheader("My Status History")

    log = get_changelog(username, resident_name=username, limit=15)
    if not log:
        st.caption("No status updates recorded yet.")
    else:
        rows = []
        for entry in log:
            rows.append({
                "When":   _fmt_dt(entry.get("changed_at")),
                "Status": entry.get("new_status", "—"),
                "Note":   entry.get("note", ""),
            })
        df_log = pd.DataFrame(rows)

        # Color the Status column
        def _color_status(val):
            if val == "Evacuated":
                return "background-color: #1e3a1e; color: #5cb85c"
            elif val == "Not Evacuated":
                return "background-color: #3a1e1e; color: #e05c5c"
            return ""

        st.dataframe(
            df_log.style.applymap(_color_status, subset=["Status"]),
            use_container_width=True,
            hide_index=True,
        )