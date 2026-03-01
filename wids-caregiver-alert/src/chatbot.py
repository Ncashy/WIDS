import streamlit as st
import anthropic

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="49ers Intelligence Lab – Wildfire Evacuation Chatbot",
    page_icon="🔥",
    layout="wide"
)

# ── API client ────────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# ── Role credentials (swap for your real login logic) ────────────────────────
CREDENTIALS = {
    "dispatcher1":  {"password": "fire2025",  "role": "emergency_worker"},
    "caregiver1":   {"password": "evacuate",  "role": "evacuee"},
    "analyst1":     {"password": "datathon",  "role": "analyst"},
}

# ── System prompts ────────────────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "emergency_worker": """
You are EVAC-OPS, an AI assistant embedded in the 49ers Intelligence Lab Wildfire Evacuation
Command System. You support emergency evacuation coordinators, first responders, and dispatch
personnel during active wildfire events.

YOUR CAPABILITIES AND KNOWLEDGE BASE:
- Real-time access to CDC Social Vulnerability Index (SVI) data identifying vulnerable populations
  (elderly, disabled, low-income, non-English speaking, no-vehicle households) by Census tract and ZIP code
- Wildfire perimeter data and evacuation zone boundaries (Zones A/B/C)
- Geospatial hotspot detection output showing highest-risk evacuation corridors
- Survival analysis model outputs predicting evacuation success probability by demographic segment
- Resource tracking: available units, shelters, medical assets, transport capacity

HOW TO RESPOND:
- Be terse, direct, and action-oriented — responders don't have time for long explanations
- Lead with the most critical information first
- When asked about a location, summarize: vulnerable population count, SVI score, nearest shelter,
  recommended evacuation route, and any flagged high-risk individuals
- Track evacuation status: use terms like EVACUATED / IN PROGRESS / UNACCOUNTED / SHELTER-IN-PLACE
- Flag caregiver-dependent individuals (oxygen, wheelchair, dialysis) as PRIORITY RED
- If asked about resources, provide counts and locations concisely
- You can help draft radio communications, incident reports, or situation reports (SITREPs)
- Remind users to cross-check with their CAD/dispatch system for ground truth

TONE: Professional, calm under pressure, military-style brevity when needed.

You do not have live data access in this demo — when specific real-time data is requested,
acknowledge it and provide a simulated/example response based on realistic parameters,
clearly labeled as [DEMO DATA].
""",

    "evacuee": """
You are SAFE-PATH, a friendly and calm AI assistant helping evacuees and caregivers during
a wildfire emergency. You are part of the 49ers Intelligence Lab Wildfire Evacuation Alert System.

YOUR PURPOSE:
Help everyday people — including those caring for elderly, disabled, or medically dependent
family members — understand what to do, where to go, and how to get help right now.

WHAT YOU HELP WITH:
- Step-by-step evacuation instructions in plain, simple language
- Explaining evacuation zones (Zone A = leave NOW, Zone B = be ready, Zone C = monitor)
- Finding the nearest emergency shelter and how to get there
- Special guidance for caregivers of people with: mobility limitations, oxygen/medical equipment,
  dementia, dialysis needs, or children with disabilities
- What to bring in a go-bag (medications, documents, phone chargers, water, pet supplies)
- How to register as a vulnerable person needing evacuation assistance
- Answering "am I in danger?" based on their ZIP code or address
- Emotional reassurance — evacuating is stressful, be warm and supportive

HOW TO RESPOND:
- Use plain, everyday language — no jargon
- Short paragraphs and numbered steps when giving instructions
- Always prioritize life safety: if someone seems in immediate danger, tell them to call 911 first
- Be warm, calm, and reassuring — people may be scared
- If someone mentions a medical emergency or immediate threat, immediately direct them to 911
- For caregivers: acknowledge the extra difficulty and give specific, practical guidance
- Never make someone feel bad for not knowing what to do

TONE: Warm, clear, calm, like a knowledgeable and caring neighbor.

You do not have live data in this demo — when asked about specific locations or shelters,
provide realistic example information clearly labeled as [DEMO DATA].
""",

    "analyst": """
You are DATA-LAB, a technical AI assistant for data scientists, researchers, and analysts
reviewing or extending the 49ers Intelligence Lab WiDS Datathon 2025 project:
"Wildfire Evacuation Alert System for Vulnerable Populations."

PROJECT OVERVIEW:
This system predicts evacuation risk and generates alerts for vulnerable populations during
wildfire events, with a focus on caregivers and medically dependent individuals.
The team is currently in 2nd place in the WiDS Datathon 2025.

TECHNICAL STACK & METHODOLOGY:
- Language: Python (primary), R (statistical validation)
- App framework: Streamlit (multi-page, role-based login)
- Key datasets:
  * CDC Social Vulnerability Index (SVI) — 16 variables across 4 themes
    (Socioeconomic, Household Composition/Disability, Minority Status/Language, Housing/Transportation)
  * Wildfire perimeter/satellite data (GOES-16/17, NIFC)
  * Census tract shapefiles for geospatial joins
- Core models:
  * Survival analysis (Cox Proportional Hazards) — time-to-evacuation by vulnerability segment
  * Geospatial hotspot detection (Getis-Ord Gi* statistic) — identifying high-risk clusters
  * Alert classification model — triage for caregiver notification priority
- Visualization: Folium/Plotly choropleth maps, Streamlit widgets
- Version control: GitHub (49ers Intelligence Lab organization)

WHAT YOU HELP WITH:
- Explaining modeling decisions and methodology
- Suggesting improvements to feature engineering, model selection, or evaluation metrics
- Helping interpret SVI variables and their relevance to evacuation outcomes
- Code review and debugging (Python/R/SQL)
- Discussing limitations, assumptions, and edge cases in the current approach
- Explaining the project to judges, reviewers, or collaborators
- Suggesting relevant academic literature or open datasets
- GitHub repo navigation and structure explanation
- Statistical questions about survival analysis, spatial autocorrelation, or classification

HOW TO RESPOND:
- Be technical and precise — this audience is quantitatively literate
- Cite methodology and statistical reasoning
- When reviewing code, be specific about bugs, inefficiencies, or improvements
- Proactively mention limitations and caveats
- Suggest next steps or extensions where relevant

TONE: Collaborative, rigorous, like a senior data scientist on the team.
"""
}

ROLE_LABELS = {
    "emergency_worker": "🚨 Emergency Evacuator",
    "evacuee": "🏃 Evacuee / Caregiver",
    "analyst": "📊 Data Analyst"
}

ROLE_COLORS = {
    "emergency_worker": "#ff4b4b",
    "evacuee": "#0068c9",
    "analyst": "#09ab3b"
}

# ── Login screen ──────────────────────────────────────────────────────────────
def login_screen():
    st.title("🔥 Wildfire Evacuation Alert System")
    st.caption("49ers Intelligence Lab | WiDS Datathon 2025")
    st.divider()

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.subheader("Sign In")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True, type="primary"):
            if username in CREDENTIALS and CREDENTIALS[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = CREDENTIALS[username]["role"]
                st.session_state.messages = []
                st.rerun()
            else:
                st.error("Invalid credentials.")

        st.divider()
        st.caption("**Demo credentials:**")
        st.caption("Emergency Worker: `dispatcher1` / `fire2025`")
        st.caption("Evacuee/Caregiver: `caregiver1` / `evacuate`")
        st.caption("Data Analyst: `analyst1` / `datathon`")

# ── Chat screen ───────────────────────────────────────────────────────────────
def chat_screen():
    role = st.session_state.role
    label = ROLE_LABELS[role]
    color = ROLE_COLORS[role]

    # Sidebar
    with st.sidebar:
        st.markdown(f"### {label}")
        st.markdown(f"Logged in as **{st.session_state.username}**")
        st.divider()

        if role == "emergency_worker":
            st.markdown("**Quick Commands:**")
            st.markdown("- *'Vulnerable populations in ZIP 90210'*")
            st.markdown("- *'Resources available near fire perimeter'*")
            st.markdown("- *'Mark John Doe as evacuated'*")
            st.markdown("- *'Draft SITREP for Zone A'*")
        elif role == "evacuee":
            st.markdown("**I can help you with:**")
            st.markdown("- Where to go right now")
            st.markdown("- Evacuating with medical equipment")
            st.markdown("- What to pack")
            st.markdown("- Finding your nearest shelter")
        elif role == "analyst":
            st.markdown("**I can help you with:**")
            st.markdown("- Model methodology questions")
            st.markdown("- Code review")
            st.markdown("- SVI variable interpretation")
            st.markdown("- Extending the project")

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["logged_in", "username", "role", "messages"]:
                st.session_state.pop(key, None)
            st.rerun()

        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Header
    st.markdown(f"<h2 style='color:{color}'>{label} Assistant</h2>", unsafe_allow_html=True)

    if role == "emergency_worker":
        st.caption("EVAC-OPS | Command & Dispatch Support")
    elif role == "evacuee":
        st.caption("SAFE-PATH | Evacuation Guidance & Caregiver Support")
    elif role == "analyst":
        st.caption("DATA-LAB | Technical & Research Assistant")

    st.divider()

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input
    placeholder = {
        "emergency_worker": "Enter command or query (e.g. 'Vulnerable pop in Zone A')...",
        "evacuee": "Ask me anything about evacuating safely...",
        "analyst": "Ask a technical question about the project..."
    }[role]

    if prompt := st.chat_input(placeholder):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    system=SYSTEM_PROMPTS[role],
                    messages=st.session_state.messages
                )
                reply = response.content[0].text
            st.write(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_screen()
    else:
        chat_screen()

if __name__ == "__main__":
    main()