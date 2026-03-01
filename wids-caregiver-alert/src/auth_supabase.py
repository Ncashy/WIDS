"""
auth_supabase.py — Supabase-backed authentication for WiDS Wildfire Dashboard
49ers Intelligence Lab · WiDS Datathon 2025

Matches existing schema exactly:
  public.users                  — custom user table (password_hash / password_salt)
  public.user_events            — audit / navigation log
  public.evacuation_plans       — per-user jsonb plan (PK = username)
  public.caregiver_access_codes — DB-managed caregiver invite codes
  public.evacuation_status      — status CHECK IN ('Evacuated', 'Not Evacuated')
  public.evacuation_changelog   — new_status CHECK IN ('Evacuated', 'Not Evacuated')

Staff access codes (hardcoded, share only with staff):
  Emergency Worker / Dispatcher  →  DISPATCH-2025
  Data Analyst                   →  ANALYST-WiDS9

Caregiver signup is open to all community members (no code required).
An optional caregiver invite code (e.g. EVAC-DEMO2025 from caregiver_access_codes)
marks the account as caregiver_verified = true.

Test accounts — easiest to create via the signup UI, or see SQL snippet at EOF.
  caregiver_test  / WiDS@2025! / Caregiver/Evacuee
  dispatcher_test / WiDS@2025! / Emergency Worker   (code: DISPATCH-2025)
  analyst_test    / WiDS@2025! / Data Analyst        (code: ANALYST-WiDS9)
"""

import hashlib
import os
import streamlit as st
from supabase import create_client, Client
from datetime import datetime
from pathlib import Path

# ── Staff role access codes (hardcoded — never stored in DB) ─────────────────
_STAFF_CODES = {
    "Emergency Worker": "DISPATCH-2025",
    "Data Analyst":     "ANALYST-WiDS9",
}
ROLES = ["Caregiver/Evacuee", "Emergency Worker", "Data Analyst"]

# ── Evacuation statuses — must match DB CHECK constraint exactly ─────────────
EVAC_STATUSES = ["Not Evacuated", "Evacuated"]
_STATUS_COLORS = {
    "Evacuated":     "#00cc88",
    "Not Evacuated": "#AA0000",
}


# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE CLIENT
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD HELPERS  (PBKDF2-HMAC-SHA256, stdlib only — no extra deps)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_salt() -> str:
    return os.urandom(32).hex()


def _hash_password(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations=260_000,
    )
    return dk.hex()


def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
    return _hash_password(password, salt) == stored_hash


# ─────────────────────────────────────────────────────────────────────────────
# AUTH UI
# ─────────────────────────────────────────────────────────────────────────────

def render_auth_page(logo_paths=None):
    """
    Renders login / signup wall.
    Sets session_state: authenticated, username, role, user_id.
    Calls st.stop() if not authenticated.
    """
    if st.session_state.get("authenticated"):
        return

    _inject_auth_styles()

    # Center everything in a narrow middle column
    _, center, _ = st.columns([1, 2, 1])

    with center:
        if logo_paths:
            for lp in (Path(p) for p in logo_paths):
                if lp.exists():
                    _, img_col, _ = st.columns([1, 1, 1])
                    with img_col:
                        st.image(str(lp), use_container_width=True)
                    break

        st.markdown("<div class='auth-title'>49ers Intelligence Lab</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='auth-subtitle'>WiDS Datathon 2025 — Wildfire Caregiver Alert System</div>",
            unsafe_allow_html=True,
        )

        tab_in, tab_up = st.tabs(["Sign In", "Create Account"])
        with tab_in:
            _render_login_form()
        with tab_up:
            _render_signup_form()

    st.stop()


# ── Login ─────────────────────────────────────────────────────────────────────

def _render_login_form():
    with st.form("login_form", clear_on_submit=False):
        identifier = st.text_input("Username or email")
        password   = st.text_input("Password", type="password")
        submitted  = st.form_submit_button("Sign In", use_container_width=True)

    if not submitted:
        return

    if not identifier or not password:
        st.error("Please enter your username/email and password.")
        return

    sb = get_supabase()
    try:
        res = sb.table("users").select("*").eq("username", identifier).execute()
        if not res.data:
            res = sb.table("users").select("*").eq("email", identifier).execute()
        if not res.data:
            st.error("No account found with that username or email.")
            return

        user = res.data[0]
        if not _verify_password(password, user["password_salt"], user["password_hash"]):
            st.error("Incorrect password.")
            return

        # Success
        sb.table("users").update({"last_login": datetime.utcnow().isoformat()}) \
          .eq("username", user["username"]).execute()

        _log_event(user["username"], "LOGIN")
        st.session_state.update({
            "authenticated": True,
            "username":      user["username"],
            "role":          user["role"],
            "user_id":       user["id"],
        })
        st.rerun()

    except Exception as e:
        st.error(f"Sign in failed: {e}")


# ── Signup ────────────────────────────────────────────────────────────────────

def _render_signup_form():
    role_choice = st.selectbox("Account type", ROLES, key="su_role")

    if role_choice == "Caregiver/Evacuee":
        st.markdown(
            "<div class='role-note caregiver-note'>"
            "Community accounts are open to everyone — no code required. "
            "An optional caregiver invite code (e.g. <strong>EVAC-DEMO2025</strong>) "
            "will verify your account immediately."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='role-note restricted-note'>"
            f"<strong>{role_choice}</strong> accounts require an administrator "
            f"access code. Contact your system administrator if you don't have one."
            f"</div>",
            unsafe_allow_html=True,
        )

    with st.form("signup_form", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            new_username = st.text_input("Username")
        with col_b:
            new_fullname = st.text_input("Full name (optional)")

        new_email = st.text_input("Email address")

        col_c, col_d = st.columns(2)
        with col_c:
            new_pw  = st.text_input("Password (min 8 characters)", type="password")
        with col_d:
            new_pw2 = st.text_input("Confirm password", type="password")

        if role_choice == "Caregiver/Evacuee":
            access_code = st.text_input(
                "Caregiver invite code (optional)",
                placeholder="Leave blank if you don't have one",
            )
        else:
            access_code = st.text_input(
                "Administrator access code",
                placeholder="Required — contact your administrator",
            )

        col_e, col_f = st.columns(2)
        with col_e:
            zip_code = st.text_input("ZIP code (optional)")
        with col_f:
            phone = st.text_input("Phone (optional)")

        submitted = st.form_submit_button("Create Account", use_container_width=True)

    if submitted:
        _handle_signup(
            username=new_username, email=new_email, full_name=new_fullname,
            pw=new_pw, pw2=new_pw2, role=role_choice, access_code=access_code,
            zip_code=zip_code, phone=phone,
        )


def _handle_signup(username, email, full_name, pw, pw2, role, access_code, zip_code, phone):
    if not username or not email or not pw:
        st.error("Username, email, and password are required.")
        return
    if pw != pw2:
        st.error("Passwords do not match.")
        return
    if len(pw) < 8:
        st.error("Password must be at least 8 characters.")
        return

    sb = get_supabase()
    caregiver_verified = False
    caregiver_method   = ""

    # Staff roles — validate hardcoded code
    if role in _STAFF_CODES:
        if access_code.strip() != _STAFF_CODES[role]:
            st.error("Invalid access code. Contact your system administrator.")
            return

    # Caregiver — optionally validate DB invite code
    elif role == "Caregiver/Evacuee" and access_code.strip():
        try:
            code_res = (
                sb.table("caregiver_access_codes")
                .select("id, is_active")
                .eq("code", access_code.strip())
                .eq("is_active", True)
                .execute()
            )
            if code_res.data:
                caregiver_verified = True
                caregiver_method   = "invite_code"
            else:
                st.error("That caregiver invite code is not valid or has expired.")
                return
        except Exception as e:
            st.error(f"Could not verify invite code: {e}")
            return

    # Insert user
    try:
        salt   = _generate_salt()
        hashed = _hash_password(pw, salt)

        sb.table("users").insert({
            "username":                      username,
            "email":                         email,
            "full_name":                     full_name or "",
            "password_hash":                 hashed,
            "password_salt":                 salt,
            "role":                          role,
            "zip_code":                      zip_code or "",
            "phone":                         phone or "",
            "caregiver_verified":            caregiver_verified,
            "caregiver_verification_method": caregiver_method,
            "created_at":                    datetime.utcnow().isoformat(),
        }).execute()

        _log_event(username, "SIGNUP", {"role": role})
        st.success(
            f"Account created! Sign in as **{username}**."
            + (" Your caregiver account is verified." if caregiver_verified else "")
        )

    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err or "unique" in err:
            if "username" in err:
                st.error("That username is already taken.")
            elif "email" in err:
                st.error("An account with that email already exists.")
            else:
                st.error("Account already exists.")
        else:
            st.error(f"Could not create account: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR PROFILE
# ─────────────────────────────────────────────────────────────────────────────

def render_user_profile_sidebar(username: str):
    sb = get_supabase()
    try:
        p = (
            sb.table("users")
            .select("full_name, created_at, caregiver_verified")
            .eq("username", username)
            .single()
            .execute()
        )
        if p.data:
            if p.data.get("full_name"):
                st.caption(p.data["full_name"])
            joined = (p.data.get("created_at") or "")[:10]
            if joined:
                st.caption(f"Member since {joined}")
            if p.data.get("caregiver_verified"):
                st.markdown(
                    "<span style='font-size:0.72rem;background:#0d2b1e;color:#00cc88;"
                    "padding:2px 9px;border-radius:10px;border:1px solid #00cc8844'>"
                    "Verified</span>",
                    unsafe_allow_html=True,
                )
    except Exception:
        pass

    try:
        visits = (
            sb.table("user_events")
            .select("event_type, metadata, created_at")
            .eq("username", username)
            .eq("event_type", "PAGE_VISIT")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        if visits.data:
            with st.expander("Recent activity"):
                for v in visits.data:
                    page = (v.get("metadata") or {}).get("page", "—")
                    ts   = (v.get("created_at") or "")[:16].replace("T", "  ")
                    st.caption(f"{page}  ·  {ts}")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# EVENT LOGGING  →  public.user_events
# ─────────────────────────────────────────────────────────────────────────────

def _log_event(username: str, event_type: str, metadata: dict = None):
    try:
        get_supabase().table("user_events").insert({
            "username":   username,
            "event_type": event_type,
            "metadata":   metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass


def log_page_visit(username: str, page: str):
    _log_event(username, "PAGE_VISIT", {"page": page})


def sign_out(username: str):
    _log_event(username, "LOGOUT")
    for k in list(st.session_state.keys()):
        del st.session_state[k]


# ─────────────────────────────────────────────────────────────────────────────
# EVACUATION PLAN  →  public.evacuation_plans  (PK = username)
# ─────────────────────────────────────────────────────────────────────────────

def get_evacuation_plan(username: str):
    try:
        res = (
            get_supabase()
            .table("evacuation_plans")
            .select("plan_data")
            .eq("username", username)
            .single()
            .execute()
        )
        return res.data.get("plan_data") if res.data else None
    except Exception:
        return None


def save_evacuation_plan(username: str, plan_data: dict) -> bool:
    try:
        get_supabase().table("evacuation_plans").upsert(
            {"username": username, "plan_data": plan_data,
             "updated_at": datetime.utcnow().isoformat()},
            on_conflict="username",
        ).execute()
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# EVACUATION STATUS  →  public.evacuation_status
# status CHECK IN ('Evacuated', 'Not Evacuated')
# ─────────────────────────────────────────────────────────────────────────────

def _upsert_evac_status(reporter_username: str, person_name: str,
                        status: str, note: str = "") -> bool:
    if status not in EVAC_STATUSES:
        return False
    sb  = get_supabase()
    now = datetime.utcnow().isoformat()
    try:
        # Fetch previous status for changelog
        old_res = (
            sb.table("evacuation_status")
            .select("status")
            .eq("reporter_username", reporter_username)
            .eq("person_name", person_name)
            .execute()
        )
        old_status = old_res.data[0]["status"] if old_res.data else None

        # Upsert
        sb.table("evacuation_status").upsert(
            {
                "reporter_username": reporter_username,
                "person_name":       person_name,
                "status":            status,
                "note":              note,
                "updated_at":        now,
            },
            on_conflict="reporter_username,person_name",
        ).execute()

        # Changelog (only on actual change, skip gracefully if schema differs)
        if old_status != status:
            try:
                sb.table("evacuation_changelog").insert({
                    "reporter_username": reporter_username,
                    "person_name":       person_name,
                    "old_status":        old_status,
                    "new_status":        status,
                    "note":              note,
                    "changed_at":        now,
                }).execute()
            except Exception:
                pass  # changelog is non-critical

        return True
    except Exception:
        return False


def get_tracked_persons(reporter_username: str) -> list:
    try:
        res = (
            get_supabase()
            .table("evacuation_status")
            .select("*")
            .eq("reporter_username", reporter_username)
            .order("updated_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def render_evacuation_status_widget(username: str):
    """
    Full evacuation status widget — update YOUR OWN status or a MONITORED PERSON.

    Status values are binary to match the DB CHECK constraint:
      'Evacuated' | 'Not Evacuated'

    Usage in caregiver_start_page.py:
        from auth_supabase import render_evacuation_status_widget
        render_evacuation_status_widget(st.session_state.username)
    """
    st.markdown("### Update Evacuation Status")
    st.caption(
        "Report your own evacuation status or update someone you are monitoring. "
        "Emergency dispatchers can see these updates in real time."
    )

    update_for = st.radio(
        "Updating status for:",
        ["Myself", "Someone I am monitoring"],
        horizontal=True,
        key="evac_update_for",
    )

    if update_for == "Myself":
        person_name = username
        st.caption(f"Reporting as: **{username}**")
    else:
        person_name = st.text_input(
            "Person's name or identifier",
            placeholder="e.g. Mom, John Smith, Unit 4B",
            key="evac_monitored_person",
        )

    col_left, col_right = st.columns([1, 2])
    with col_left:
        status = st.radio("Status", EVAC_STATUSES, key="evac_status_radio")
        color  = _STATUS_COLORS.get(status, "#8892a4")
        st.markdown(
            f"<div style='padding:6px 12px;background:{color}22;"
            f"border:1px solid {color}66;border-radius:8px;color:{color};"
            f"font-weight:600;font-size:0.85rem;text-align:center;margin-top:4px'>"
            f"{status}</div>",
            unsafe_allow_html=True,
        )
    with col_right:
        note = st.text_area(
            "Note (location, needs, contact info)",
            height=96,
            key="evac_note_input",
            placeholder="e.g. At Westside shelter, needs medication pickup",
        )

    if st.button("Save Status", key="evac_save_btn", use_container_width=True, type="primary"):
        name = (person_name or "").strip()
        if not name:
            st.error("Please enter a name or identifier for the person.")
        else:
            ok = _upsert_evac_status(username, name, status, note)
            if ok:
                _log_event(username, "EVAC_STATUS_UPDATE", {"person": name, "status": status})
                st.success(f"Saved — **{name}** is now marked as **{status}**.")
            else:
                st.error("Failed to save. Please check your connection and try again.")

    # ── Tracked persons list ───────────────────────────────────────────────────
    tracked = get_tracked_persons(username)
    if tracked:
        st.markdown("---")
        st.markdown("**People you are monitoring:**")
        for p in tracked:
            c    = _STATUS_COLORS.get(p.get("status", "Not Evacuated"), "#8892a4")
            ts   = (p.get("updated_at") or "")[:16].replace("T", "  ")
            note_txt = p.get("note") or ""
            st.markdown(
                f"<div style='padding:10px 14px;background:rgba(128,128,128,0.06);"
                f"border-radius:10px;border-left:4px solid {c};margin:6px 0'>"
                f"<span style='font-weight:600'>{p['person_name']}</span> "
                f"<span style='background:{c}22;color:{c};padding:2px 9px;"
                f"border-radius:12px;font-size:0.82rem'>{p.get('status', '—')}</span><br>"
                f"<span style='font-size:0.8rem;opacity:0.65'>"
                f"{note_txt}{'  ·  ' if note_txt else ''}{ts}</span></div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────────────────

def _inject_auth_styles():
    st.markdown("""
    <style>
    .auth-title {
        text-align: center;
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        margin-top: 0.4rem;
        margin-bottom: 0.2rem;
    }
    .auth-subtitle {
        text-align: center;
        font-size: 0.88rem;
        opacity: 0.6;
        margin-bottom: 2rem;
    }
    .role-note {
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 0.84rem;
        margin-bottom: 0.8rem;
        line-height: 1.5;
    }
    .caregiver-note  { background:#edfaf4; border-left:3px solid #00a86b; color:#1a6645; }
    .restricted-note { background:#fdf6e3; border-left:3px solid #B3995D; color:#7a5c1e; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER SQL — run in Supabase SQL editor to add missing columns if needed
# ─────────────────────────────────────────────────────────────────────────────
# If evacuation_status is missing reporter_username / person_name / note:
#
#   ALTER TABLE public.evacuation_status
#     ADD COLUMN IF NOT EXISTS reporter_username text,
#     ADD COLUMN IF NOT EXISTS person_name       text DEFAULT 'self',
#     ADD COLUMN IF NOT EXISTS note              text DEFAULT '',
#     ADD COLUMN IF NOT EXISTS updated_at        timestamptz DEFAULT now();
#
#   ALTER TABLE public.evacuation_status
#     DROP CONSTRAINT IF EXISTS evac_status_unique_person,
#     ADD CONSTRAINT evac_status_unique_person
#       UNIQUE (reporter_username, person_name);
#
# If evacuation_changelog is missing reporter_username / person_name / old_status / changed_at:
#
#   ALTER TABLE public.evacuation_changelog
#     ADD COLUMN IF NOT EXISTS reporter_username text,
#     ADD COLUMN IF NOT EXISTS person_name       text DEFAULT 'self',
#     ADD COLUMN IF NOT EXISTS old_status        text,
#     ADD COLUMN IF NOT EXISTS note              text DEFAULT '',
#     ADD COLUMN IF NOT EXISTS changed_at        timestamptz DEFAULT now();
#
# To create test accounts quickly — run this Python snippet locally to get hashes:
#   import hashlib, os
#   for name, pw, role in [
#       ('caregiver_test',  'WiDS@2025!', 'Caregiver/Evacuee'),
#       ('dispatcher_test', 'WiDS@2025!', 'Emergency Worker'),
#       ('analyst_test',    'WiDS@2025!', 'Data Analyst'),
#   ]:
#       salt = os.urandom(32).hex()
#       hsh  = hashlib.pbkdf2_hmac('sha256', pw.encode(), bytes.fromhex(salt), 260000).hex()
#       print(f"INSERT INTO public.users (username,email,password_hash,password_salt,role)")
#       print(f"VALUES ('{name}','{name}@wids.test','{hsh}','{salt}','{role}');")