import streamlit as st

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="TerravaultIQ Lead Intelligence",
    page_icon="📍",
    layout="wide"
)

# ---------------------------
# STYLES
# ---------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #f4f6f1 0%, #eef5ef 100%);
    }

    .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }

    h1, h2, h3 {
        color: #0f234a;
    }

    .tvq-hero {
        background: white;
        border-radius: 24px;
        padding: 30px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }

    .tvq-badge {
        background: #d1fae5;
        color: #065f46;
        padding: 6px 14px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 12px;
        display: inline-block;
        margin-bottom: 12px;
    }

    div.stButton > button {
        background: #22c55e;
        color: white;
        border-radius: 999px;
        font-weight: 700;
        border: none;
        padding: 10px 18px;
    }

    div.stButton > button:hover {
        background: #16a34a;
        color: white;
    }

    a {
        color: #0b7a6e;
        font-weight: 600;
        text-decoration: none;
    }

    a:hover {
        text-decoration: underline;
    }

    .tvq-card {
        background: white;
        padding: 20px;
        border-radius: 18px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# NAV LINK
# ---------------------------
st.markdown("""
<a href="https://terravaultiq-app-five.vercel.app/platform" target="_self">
← Back to Platform
</a>
""", unsafe_allow_html=True)

# ---------------------------
# HERO
# ---------------------------
st.markdown("""
<div class="tvq-hero">
    <div class="tvq-badge">TerravaultIQ</div>
    <h1>Lead Intelligence Engine</h1>
    <p>Discover high-value leads, analyze websites, and build outreach-ready prospect lists.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# INPUT SECTION
# ---------------------------
st.markdown('<div class="tvq-card">', unsafe_allow_html=True)

api_key = st.text_input("Google API Key", type="password")

col1, col2 = st.columns(2)

with col1:
    lead_type = st.selectbox("Lead Type", ["roofers", "plumbers", "dentists", "restaurants"])
    keyword = st.text_input("Search Keyword", "roofers")
    city = st.text_input("City or Area", "Leavenworth, KS")

with col2:
    radius = st.slider("Radius (miles)", 5, 100, 25)
    max_sites = st.slider("Max websites to audit", 5, 200, 50)

include_no_website = st.checkbox("Include businesses with no website", value=True)
audit_websites = st.checkbox("Audit websites for outreach data", value=True)

run_search = st.button("Find Leads")

st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# RESULTS (PLACEHOLDER)
# ---------------------------
if run_search:
    if not api_key:
        st.error("Please enter your Google API key")
    else:
        st.success("Running search...")

        # Placeholder results (replace with your real logic)
        fake_results = [
            {"name": "ABC Roofing", "city": city, "phone": "(555) 123-4567"},
            {"name": "TopLine Roofing", "city": city, "phone": "(555) 222-9999"},
            {"name": "Prime Roof Co", "city": city, "phone": "(555) 888-1212"},
        ]

        st.markdown("### Results")

        for lead in fake_results:
            st.markdown(f"""
            <div class="tvq-card">
                <strong>{lead['name']}</strong><br>
                {lead['city']}<br>
                {lead['phone']}
            </div>
            """, unsafe_allow_html=True)

        st.download_button(
            "Download Leads (CSV)",
            data="name,city,phone\nABC Roofing,City,(555)\n",
            file_name="leads.csv"
        )