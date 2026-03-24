import re
from urllib.parse import urljoin

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Lead Engine V5", layout="wide")

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r'(\+?1?[\s\-.]?)?(\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})')
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
META_DESC_RE = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)

HEADERS = {"User-Agent": "LeadEngineV5/1.0"}

BUSINESS_PRESETS = {
    "roofers": "roofers",
    "cleaning companies": "cleaning companies",
    "med spas": "med spas",
    "lawn care": "lawn care",
    "contractors": "contractors",
    "real estate": "real estate agents",
    "salons": "hair salons",
    "dentists": "dentists",
    "property managers": "property management",
    "apartments": "apartments",
    "plumbers": "plumbers",
    "electricians": "electricians",
    "painters": "painters",
    "restaurants": "restaurants",
    "custom": "",
}

CRM_COLUMNS = [
    "status", "priority", "notes", "owner", "last_contacted", "follow_up_date", "offer_angle"
]

def normalize_website(website: str) -> str:
    website = str(website).strip()
    if not website:
        return ""
    if not website.startswith("http://") and not website.startswith("https://"):
        website = "https://" + website
    return website

def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(text)).replace("\n", " ").replace("\r", " ").strip()

def geocode_google(api_key: str, place: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": place, "key": api_key}
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"Google Geocoding error: {data.get('status', 'unknown')}")
    result = data["results"][0]
    loc = result["geometry"]["location"]
    return loc["lat"], loc["lng"], result["formatted_address"]

def places_search(api_key: str, query: str, lat: float, lng: float, radius_m: int, max_pages: int = 3):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    results = []
    next_page_token = None

    for page in range(max_pages):
        params = {"query": query, "location": f"{lat},{lng}", "radius": radius_m, "key": api_key}
        if next_page_token:
            import time
            time.sleep(2.5)
            params = {"pagetoken": next_page_token, "key": api_key}
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            if status == "INVALID_REQUEST" and next_page_token:
                continue
            raise ValueError(f"Google Places error: {status}")
        results.extend(data.get("results", []))
        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break
    return results

def get_place_details(api_key: str, place_id: str):
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    fields = ",".join([
        "name", "website", "formatted_phone_number", "international_phone_number",
        "formatted_address", "url", "rating", "user_ratings_total", "types"
    ])
    params = {"place_id": place_id, "fields": fields, "key": api_key}
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "OK":
        return {}
    return data.get("result", {})

def website_audit(website: str):
    website = normalize_website(website)
    empty = {
        "site_live": "no_website",
        "final_url": "",
        "emails_found": "",
        "phones_found": "",
        "facebook_link": "",
        "instagram_link": "",
        "title": "",
        "meta_description": "",
        "h1": "",
        "bad_website_score": 100,
        "website_notes": "No website found",
        "offer_angle": "Website build or landing page angle",
        "website_status": "missing_website",
    }
    if not website:
        return empty

    pages = [website, urljoin(website, "/contact"), urljoin(website, "/about"), urljoin(website, "/services")]
    emails = set()
    phones = set()
    facebook = ""
    instagram = ""
    title = ""
    meta_desc = ""
    h1 = ""
    site_live = "no"
    final_url = website
    notes = []
    score = 0

    for i, page in enumerate(pages):
        try:
            r = requests.get(page, headers=HEADERS, timeout=15, allow_redirects=True)
            if i == 0:
                final_url = r.url
            if r.ok:
                site_live = "yes"
                text = r.text[:250000]
                for m in EMAIL_RE.findall(text):
                    mm = m.lower()
                    if not mm.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
                        emails.add(m)
                for pm in PHONE_RE.findall(text):
                    phones.add("".join(pm).strip())
                if not facebook:
                    m = re.search(r'https?://[^\s"\'<>]*facebook\.com/[^\s"\'<>]+', text, re.I)
                    if m:
                        facebook = m.group(0)
                if not instagram:
                    m = re.search(r'https?://[^\s"\'<>]*instagram\.com/[^\s"\'<>]+', text, re.I)
                    if m:
                        instagram = m.group(0)
                if not title:
                    m = TITLE_RE.search(text)
                    if m:
                        title = strip_tags(m.group(1))[:140]
                if not meta_desc:
                    m = META_DESC_RE.search(text)
                    if m:
                        meta_desc = strip_tags(m.group(1))[:220]
                if not h1:
                    m = H1_RE.search(text)
                    if m:
                        h1 = strip_tags(m.group(1))[:160]
        except Exception:
            pass

    if site_live != "yes":
        score += 45
        notes.append("Website did not load cleanly")
    if not final_url.startswith("https://"):
        score += 10
        notes.append("Website is not on HTTPS")
    if not title:
        score += 10
        notes.append("Missing page title")
    if not meta_desc:
        score += 15
        notes.append("Missing meta description")
    if not h1:
        score += 8
        notes.append("Missing H1 heading")
    if not emails:
        score += 5
    if not phones:
        score += 5
    if not facebook and not instagram:
        score += 5
        notes.append("No social links found")

    score = max(0, min(score, 100))
    if score >= 70:
        offer = "Strong website rebuild angle"
    elif score >= 40:
        offer = "Website tune-up or lead page angle"
    else:
        offer = "SEO, ads, or conversion angle"

    return {
        "site_live": site_live,
        "final_url": final_url,
        "emails_found": ", ".join(sorted(emails)[:5]),
        "phones_found": ", ".join(sorted(phones)[:5]),
        "facebook_link": facebook,
        "instagram_link": instagram,
        "title": title,
        "meta_description": meta_desc,
        "h1": h1,
        "bad_website_score": score,
        "website_notes": " | ".join(notes) if notes else "Website looks usable",
        "offer_angle": offer,
        "website_status": "has_website",
    }

def add_priority(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "bad_website_score" not in df.columns:
        df["bad_website_score"] = 0
    score = pd.to_numeric(df["bad_website_score"], errors="coerce").fillna(0)
    no_site = df["website"].astype(str).str.strip() == ""
    df["priority"] = "medium"
    df.loc[no_site, "priority"] = "high"
    df.loc[score >= 50, "priority"] = "high"
    df.loc[(score < 20) & (~no_site), "priority"] = "low"
    return df

def finish_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str)
    subset = [c for c in ["name", "address", "website"] if c in df.columns]
    if subset:
        df = df.drop_duplicates(subset=subset)
    for c in CRM_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    if "status" in df.columns:
        df["status"] = df["status"].replace("", "new")
    return df.reset_index(drop=True)

def build_leads_from_google(api_key: str, business_type: str, keyword: str, area: str, radius_miles: int, detail_limit: int):
    lat, lng, formatted_area = geocode_google(api_key, area)
    radius_m = int(radius_miles * 1609.34)
    query = f"{keyword} in {formatted_area}"
    search_results = places_search(api_key, query, lat, lng, radius_m)

    rows = []
    for item in search_results:
        place_id = item.get("place_id", "")
        details = get_place_details(api_key, place_id) if place_id else {}
        rows.append({
            "name": details.get("name") or item.get("name", ""),
            "business_type": business_type,
            "search_keyword": keyword,
            "search_area": formatted_area,
            "address": details.get("formatted_address") or item.get("formatted_address", ""),
            "website": details.get("website", ""),
            "phone": details.get("formatted_phone_number") or details.get("international_phone_number", ""),
            "rating": details.get("rating", item.get("rating", "")),
            "ratings_total": details.get("user_ratings_total", item.get("user_ratings_total", "")),
            "google_maps_url": details.get("url", ""),
            "place_id": place_id,
            "types": ", ".join(details.get("types", item.get("types", []))),
        })

    df = finish_df(pd.DataFrame(rows))
    if df.empty:
        return df, formatted_area

    if detail_limit > 0:
        for col in ["site_live","final_url","emails_found","phones_found","facebook_link","instagram_link",
                    "title","meta_description","h1","bad_website_score","website_notes","offer_angle","website_status"]:
            if col not in df.columns:
                df[col] = ""
        count = 0
        for idx in df.index:
            website = str(df.at[idx, "website"]).strip()
            if not website:
                df.at[idx, "bad_website_score"] = "100"
                df.at[idx, "website_notes"] = "No website found"
                df.at[idx, "offer_angle"] = "Website build or landing page angle"
                df.at[idx, "website_status"] = "missing_website"
                continue
            if count >= detail_limit:
                continue
            audit = website_audit(website)
            for k, v in audit.items():
                df.at[idx, k] = v
            count += 1
    df = add_priority(df)
    return finish_df(df), formatted_area

st.title("Lead Engine V5")
st.write("A stronger local prospecting tool powered by your Google API key.")

with st.expander("What V5 does", expanded=True):
    st.write("""
- Google-based business discovery
- Businesses with missing websites
- Weak website scoring
- Public email, phone, Facebook, and Instagram pull from websites
- CRM columns for notes and follow-up
- CSV export
- No file editing required — paste your API key into the app
""")

tab1, tab2 = st.tabs(["Find leads", "Upload & enrich CSV"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        api_key = st.text_input("Google API Key", type="password", help="Paste your API key here. It stays in this browser session.")
        preset = st.selectbox("Lead type", list(BUSINESS_PRESETS.keys()), index=0)
        default_keyword = BUSINESS_PRESETS[preset] if preset != "custom" else ""
        keyword = st.text_input("Search word", value=default_keyword or "roofers")
        area = st.text_input("City or area", value="Leavenworth, KS")
    with c2:
        radius = st.slider("Radius (miles)", 1, 100, 25, 1)
        keep_no_website = st.checkbox("Keep businesses with no website", value=True)
        audit_sites = st.checkbox("Check websites for real details", value=True)
        audit_limit = st.slider("Max websites to check", 0, 100, 20, 5)
        run = st.button("Find Leads")

    if run:
        if not api_key.strip():
            st.error("Paste your Google API key first.")
        else:
            try:
                limit = audit_limit if audit_sites else 0
                df, formatted_area = build_leads_from_google(api_key.strip(), preset, keyword.strip(), area.strip(), radius, limit)
                if not keep_no_website and not df.empty:
                    df = df[df["website"].str.strip() != ""].copy()
                df = finish_df(df)
                if df.empty:
                    st.warning("No results found.")
                else:
                    a, b, c, d = st.columns(4)
                    a.metric("Total leads", len(df))
                    b.metric("With website", int((df["website"].astype(str).str.strip() != "").sum()))
                    c.metric("Without website", int((df["website"].astype(str).str.strip() == "").sum()))
                    d.metric("High priority", int((df["priority"].astype(str) == "high").sum()) if "priority" in df.columns else 0)
                    st.success(f"Searching near: {formatted_area}")
                    st.dataframe(df, use_container_width=True, height=520)
                    st.download_button(
                        "Download CSV",
                        data=df.to_csv(index=False).encode("utf-8"),
                        file_name="lead_engine_v5_export.csv",
                        mime="text/csv",
                    )
            except Exception as e:
                st.error(str(e))

with tab2:
    st.subheader("Upload & enrich CSV")
    st.write("Use this for your own lead lists. You only need a website column to score and enrich them.")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    c1, c2 = st.columns(2)
    with c1:
        name_col = st.text_input("Name column", value="name", key="up_name")
        website_col = st.text_input("Website column", value="website", key="up_web")
    with c2:
        enrich_limit = st.slider("Max uploaded websites to check", 0, 200, 25, 5)
        run_upload = st.button("Enrich Uploaded CSV")
    if uploaded is not None and run_upload:
        raw = pd.read_csv(uploaded)
        if name_col not in raw.columns:
            raw[name_col] = ""
        if website_col not in raw.columns:
            raw[website_col] = ""
        work = raw.copy()
        work["name"] = work[name_col].fillna("").astype(str)
        work["website"] = work[website_col].fillna("").astype(str)
        work = finish_df(work)
        if enrich_limit > 0:
            for col in ["site_live","final_url","emails_found","phones_found","facebook_link","instagram_link",
                        "title","meta_description","h1","bad_website_score","website_notes","offer_angle","website_status"]:
                if col not in work.columns:
                    work[col] = ""
            count = 0
            for idx in work.index:
                website = str(work.at[idx, "website"]).strip()
                if not website:
                    work.at[idx, "bad_website_score"] = "100"
                    work.at[idx, "website_notes"] = "No website found"
                    work.at[idx, "offer_angle"] = "Website build or landing page angle"
                    continue
                if count >= enrich_limit:
                    continue
                audit = website_audit(website)
                for k, v in audit.items():
                    work.at[idx, k] = v
                count += 1
        work = add_priority(work)
        work = finish_df(work)
        st.dataframe(work, use_container_width=True, height=520)
        st.download_button(
            "Download Enriched CSV",
            data=work.to_csv(index=False).encode("utf-8"),
            file_name="lead_engine_v5_enriched.csv",
            mime="text/csv",
        )
