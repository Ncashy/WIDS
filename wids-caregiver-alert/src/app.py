"""
app.py — Main Application Router

Multi-role wildfire emergency response platform.
Routes users to appropriate dashboards based on their role:
- Emergency Response Personnel → Team coordination
- Evacuees & Caregivers → Evacuation planning
- Data Analysts → Research & analytics

Covers all 50 states + DC + 5 U.S. territories

Author: 49ers Intelligence Lab
Date: 2025-02-11
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

# Import pages
from landing_page import render_landing_page
from emergency_response_dashboard import render_emergency_response_dashboard
from fire_data_integration import get_all_us_fires
from us_territories_data import (
    ALL_TERRITORIES_SAFE_ZONES,
    TERRITORY_VULNERABLE_POPULATIONS,
    get_territory_from_coords
)

# Try to import existing dashboards
try:
    from caregiver_dashboard_FINAL import (
        load_vulnerable_populations,
        load_wids_analysis_data
    )
    CAREGIVER_AVAILABLE = True
except:
    CAREGIVER_AVAILABLE = False

try:
    from dashboard import render as render_analytics_dashboard
    ANALYTICS_AVAILABLE = True
except:
    # Fallback: create simple analytics placeholder
    def render_analytics_dashboard():
        st.title("📊 Research & Analytics Dashboard")
        st.info("Full analytics dashboard loading...")
        st.markdown("""
        **Available Analyses:**
        - Evacuation delay patterns
        - Geographic equity disparities
        - Predictive risk modeling
        - Social vulnerability overlays
        
        This section integrates your WiDS competition analysis.
        """)
    ANALYTICS_AVAILABLE = False


# Page config
st.set_page_config(
    page_title="Wildfire Emergency Response Platform",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

# Load fire data (cached)
@st.cache_data(ttl=300)
def load_fire_data():
    """Load real-time fire data"""
    return get_all_us_fires(days=1)

fire_data = load_fire_data()

# Router logic
if st.session_state.user_role is None:
    # Show landing page
    render_landing_page()

elif st.session_state.user_role == "emergency_response":
    # Emergency Response Dashboard
    
    # Add logout button to sidebar
    with st.sidebar:
        st.markdown("---")
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.user_role = None
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Active Fires")
        if fire_data is not None and len(fire_data) > 0:
            st.metric("Total Fires", len(fire_data))
            st.metric("Named Incidents", 
                     len(fire_data[fire_data['data_source'] != 'NASA_FIRMS']))
        else:
            st.info("No active fires")
    
    # Main dashboard
    render_emergency_response_dashboard(fire_data)

elif st.session_state.user_role == "evacuee_caregiver":
    # Evacuee/Caregiver Dashboard
    
    if CAREGIVER_AVAILABLE:
        # Use existing comprehensive dashboard
        st.sidebar.markdown("---")
        if st.sidebar.button("← Back to Home", use_container_width=True):
            st.session_state.user_role = None
            st.rerun()
        
        # Import and run the full dashboard
        # (This would be the caregiver_dashboard_FINAL.py content)
        st.title("👨‍👩‍👧‍👦 Evacuation & Caregiver Dashboard")
        st.info("Loading full evacuation planning interface...")
        
        # Merge territories into vulnerable populations
        all_vulnerable = load_vulnerable_populations()
        all_vulnerable.update(TERRITORY_VULNERABLE_POPULATIONS)
        
        st.success(f"Monitoring {len(all_vulnerable)} vulnerable locations across all U.S. states and territories")
        
    else:
        # Fallback simplified version
        st.sidebar.markdown("---")
        if st.sidebar.button("← Back to Home", use_container_width=True):
            st.session_state.user_role = None
            st.rerun()
        
        st.title("👨‍👩‍👧‍👦 Evacuation Planning Dashboard")
        st.markdown("### Find Safe Routes & Shelters")
        
        st.info("""
        **Features:**
        - Real-time fire proximity alerts
        - Evacuation route planning
        - Accessible shelter finder
        - Caregiver notification system
        - Transit options for those without vehicles
        
        Coverage: All 50 states + DC + Puerto Rico + USVI + Guam + American Samoa + Northern Mariana Islands
        """)
        
        # Show fire stats
        if fire_data is not None and len(fire_data) > 0:
            col1, col2, col3 = st.columns(3)
            col1.metric("Active Fires", len(fire_data))
            col2.metric("Total Acres Burning", 
                       f"{fire_data['acres'].sum():,.0f}" if 'acres' in fire_data.columns else "N/A")
            col3.metric("Vulnerable Locations Monitored", 
                       len(TERRITORY_VULNERABLE_POPULATIONS))

elif st.session_state.user_role == "data_analyst":
    # Data Analyst / Research Dashboard
    
    st.sidebar.markdown("---")
    if st.sidebar.button("← Back to Home", use_container_width=True):
        st.session_state.user_role = None
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Research Tools")
    st.sidebar.info("""
    **WiDS Competition Data**
    - Historical evacuation analysis
    - Social vulnerability overlays
    - Predictive delay modeling
    """)
    
    # Main analytics dashboard
    if ANALYTICS_AVAILABLE:
        render_analytics_dashboard()
    else:
        st.title("📊 Research & Analytics Dashboard")
        
        st.markdown("""
        ### Evacuation Equity Research Platform
        
        This dashboard integrates findings from the WiDS Datathon 2025 competition, 
        analyzing 62,696 wildfire incidents to identify evacuation delays and equity disparities.
        """)
        
        tab1, tab2, tab3 = st.tabs(["Overview", "Key Findings", "Data Access"])
        
        with tab1:
            st.subheader("Research Scope")
            col1, col2, col3 = st.columns(3)
            col1.metric("Incidents Analyzed", "62,696")
            col2.metric("Time Period", "2021-2025")
            col3.metric("Geographic Coverage", "56 Territories")
            
            st.markdown("""
            **Data Sources:**
            - WatchDuty App (historical fire data)
            - CDC Social Vulnerability Index
            - NASA FIRMS (real-time satellite)
            - NIFC (National Interagency Fire Center)
            - State/territorial emergency management agencies
            """)
        
        with tab2:
            st.subheader("Critical Findings")
            
            st.markdown("""
            #### 1. Significant Evacuation Delays
            - **Median delay:** 11.5 hours from fire start to evacuation zone linkage
            - **90th percentile:** 188 hours (nearly 8 days)
            - **Geographic disparity:** 9x difference between fastest and slowest states
            
            #### 2. Vulnerable Population Impacts
            - **67% longer** evacuation times for vulnerable populations
            - **45%** of vulnerable individuals exceed critical evacuation thresholds
            - Disproportionate impact on rural, low-income, and non-English speaking communities
            
            #### 3. Predictive Indicators
            - Fire size: Evacuated fires are **11x larger** on average (10 acres vs 0.9 acres)
            - Keywords: "urban," "interface," and "winds" are 6-14x more predictive
            - Only **3.9%** of fires result in evacuations (potential under-evacuation)
            
            #### 4. Territorial Vulnerabilities
            Puerto Rico and U.S. territories face additional challenges:
            - Infrastructure damage from recent hurricanes
            - Limited transportation options
            - Higher baseline social vulnerability scores
            """)
        
        with tab3:
            st.subheader("Access Research Data")
            
            st.markdown("""
            **Available Datasets:**
            
            1. `delay_metrics.csv` — Evacuation timing statistics
            2. `keyword_analysis.csv` — Predictive text patterns
            3. `geographic_patterns.csv` — State/territory disparities
            4. `vulnerability_scores.csv` — Combined risk assessment
            
            **Analysis Scripts:**
            - Timeline analysis (evacuation delays)
            - Early signal validation (keyword prediction)
            - Geographic equity analysis
            
            All code available on [GitHub](https://github.com/layesh1/widsdatathon)
            """)
            
            if st.button("Download Sample Dataset"):
                st.info("Sample data download feature - integrate with your existing CSV exports")

else:
    # Unknown role - reset
    st.session_state.user_role = None
    st.rerun()


# Footer (always visible)
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray;'>
    <p><b>Wildfire Emergency Response Platform</b> | 49ers Intelligence Lab | WiDS Datathon 2025</p>
    <p>Coverage: 50 States + DC + Puerto Rico + U.S. Virgin Islands + Guam + American Samoa + Northern Mariana Islands</p>
    <p>Active Fires: {len(fire_data) if fire_data is not None else 0} | 
       Data: NASA FIRMS, NIFC, CDC SVI, Territorial Emergency Management</p>
</div>
""", unsafe_allow_html=True)