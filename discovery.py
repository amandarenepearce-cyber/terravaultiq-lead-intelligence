import os
from urllib.parse import quote
import requests

USER_AGENT = 'lead-intelligence-engine-v3/1.0'

KEYWORD_MAP = {
    'roofing': ['roof', 'roofer', 'roofing', 'roof repair', 'siding', 'gutters'],
    'roofer': ['roof', 'roofer', 'roofing', 'roof repair', 'siding', 'gutters'],
    'plumber': ['plumb', 'plumber', 'plumbing', 'drain'],
    'plumbing': ['plumb', 'plumber', 'plumbing', 'drain'],
    'hvac': ['hvac', 'heating', 'cooling', 'air conditioning'],
    'cleaner': ['clean', 'cleaner', 'cleaning', 'maids', 'housekeeping'],
    'cleaning': ['clean', 'cleaner', 'cleaning', 'maids', 'housekeeping'],
    'moving': ['moving', 'mover', 'movers', 'relocation'],
    'mover': ['moving', 'mover', 'movers', 'relocation'],
    'junk removal': ['junk', 'hauling', 'removal'],
    'landscaping': ['landscap', 'lawn', 'tree', 'irrigation'],
    'painting': ['paint', 'painter', 'painting'],
    'real estate': ['real estate', 'realtor', 'estate agent', 'broker'],
    'mortgage': ['mortgage', 'loan', 'lender'],
    'med spa': ['med spa', 'spa', 'aesthetics', 'botox'],
}

def keyword_terms(keyword):
    key = (keyword or '').strip().lower()
    terms = []
    for k, vals in KEYWORD_MAP.items():
        if k in key or key in k:
            terms.extend(vals)
    if not terms:
        terms = [t for t in key.replace(',', ' ').split() if t]
    return list(dict.fromkeys(terms))

def keyword_match(text, keyword):
    txt = (text or '').lower()
    terms = keyword_terms(keyword)
    return any(term in txt for term in terms)

def haversine_miles(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, asin, sqrt
    r = 3958.8
    a = sin(radians(lat2-lat1)/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(radians(lon2-lon1)/2)**2
    return 2*r*asin(sqrt(a))

def geocode_zip(zip_code):
    url = 'https://nominatim.openstreetmap.org/search'
    params = {'postalcode': zip_code, 'country': 'USA', 'format': 'jsonv2', 'limit': 1}
    r = requests.get(url, params=params, headers={'User-Agent': USER_AGENT}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError(f'Could not geocode ZIP code {zip_code}')
    row = data[0]
    return float(row['lat']), float(row['lon'])

def get_google_places_key():
    return os.getenv('GOOGLE_PLACES_API_KEY', '').strip()

def get_google_cse_key():
    return os.getenv('GOOGLE_CSE_API_KEY', '').strip()

def get_google_cse_cx():
    return os.getenv('GOOGLE_CSE_CX', '').strip()

def google_search_places(lat, lon, radius, keyword, zip_code):
    api_key = get_google_places_key()
    if not api_key:
        return []
    terms = keyword_terms(keyword)
    queries = [f'{keyword} near {zip_code}', f'{keyword} company near {zip_code}', f'{keyword} service near {zip_code}']
    queries += [f'{term} near {zip_code}' for term in terms[:3]]
    out, seen = [], set()
    for q in queries:
        try:
            r = requests.get(
                'https://maps.googleapis.com/maps/api/place/textsearch/json',
                params={'query': q, 'location': f'{lat},{lon}', 'radius': min(int(radius*1609.34),50000), 'key': api_key},
                timeout=20
            )
            r.raise_for_status()
            data = r.json()
        except Exception:
            data = {}
        for item in data.get('results', []):
            pid = item.get('place_id', '')
            if pid in seen:
                continue
            seen.add(pid)
            loc = item.get('geometry', {}).get('location', {})
            plat, plon = loc.get('lat'), loc.get('lng')
            if plat is None or plon is None:
                continue
            if haversine_miles(lat, lon, plat, plon) > radius:
                continue
            searchable = ' '.join([
                item.get('name', ''),
                item.get('formatted_address', ''),
                ' '.join(item.get('types', []))
            ])
            if not keyword_match(searchable, keyword):
                continue
            out.append({
                'name': item.get('name', ''),
                'category': ', '.join(item.get('types', [])[:3]),
                'phone': '',
                'website': '',
                'public_email': '',
                'address': item.get('formatted_address', ''),
                'distance_miles': round(haversine_miles(lat, lon, plat, plon), 2),
                'rating': item.get('rating', ''),
                'review_count': item.get('user_ratings_total', ''),
                'place_id': pid,
                'data_source': 'Google Places API',
            })
    return out

def osm_search_places(lat, lon, radius, keyword):
    radius_meters = int(radius*1609.34)
    terms = keyword_terms(keyword)
    filters = []
    for term in terms[:5]:
        safe = term.replace('"', '')
        filters.extend([
            f'node["shop"~"{safe}",i](around:{{r}},{{lat}},{{lon}});',
            f'way["shop"~"{safe}",i](around:{{r}},{{lat}},{{lon}});',
            f'node["office"~"{safe}",i](around:{{r}},{{lat}},{{lon}});',
            f'way["office"~"{safe}",i](around:{{r}},{{lat}},{{lon}});',
            f'node["craft"~"{safe}",i](around:{{r}},{{lat}},{{lon}});',
            f'way["craft"~"{safe}",i](around:{{r}},{{lat}},{{lon}});',
            f'node["name"~"{safe}",i](around:{{r}},{{lat}},{{lon}});',
            f'way["name"~"{safe}",i](around:{{r}},{{lat}},{{lon}});',
        ])
    query = '[out:json][timeout:30];(' + '\n'.join(x.format(r=radius_meters, lat=lat, lon=lon) for x in filters) + ');out center tags;'
    r = requests.post('https://overpass-api.de/api/interpreter', data=query.encode('utf-8'), headers={'User-Agent': USER_AGENT}, timeout=40)
    r.raise_for_status()
    elements = r.json().get('elements', [])
    out, seen = [], set()
    for el in elements:
        tags = el.get('tags', {})
        plat = el.get('lat') or el.get('center', {}).get('lat')
        plon = el.get('lon') or el.get('center', {}).get('lon')
        if plat is None or plon is None:
            continue
        name = tags.get('name', '').strip() or 'Unknown'
        website = tags.get('website', '').strip()
        searchable = ' '.join([
            name,
            website,
            tags.get('office', ''),
            tags.get('shop', ''),
            tags.get('amenity', ''),
            tags.get('craft', ''),
        ])
        if not keyword_match(searchable, keyword):
            continue
        key = (name.lower(), round(plat, 5), round(plon, 5), website.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append({
            'name': name,
            'category': tags.get('office') or tags.get('shop') or tags.get('amenity') or tags.get('craft') or keyword,
            'phone': tags.get('phone', '').strip(),
            'website': website,
            'public_email': tags.get('email', '').strip(),
            'address': ' '.join(x for x in [tags.get('addr:housenumber', ''), tags.get('addr:street', ''), tags.get('addr:city', ''), tags.get('addr:state', ''), tags.get('addr:postcode', '')] if x),
            'distance_miles': round(haversine_miles(lat, lon, plat, plon), 2),
            'rating': '',
            'review_count': '',
            'place_id': '',
            'data_source': 'OpenStreetMap',
        })
    return out

def marketing_filter(rows, keyword):
    filtered = []
    for row in rows:
        searchable = ' '.join([
            row.get('name', ''),
            row.get('category', ''),
            row.get('address', ''),
            row.get('website', ''),
        ])
        if keyword_match(searchable, keyword):
            filtered.append(row)
    return filtered

def discover_businesses(zip_code, radius, mode, custom_keyword='', use_google=False, use_osm=True):
    lat, lon = geocode_zip(zip_code)
    rows = []
    keyword = custom_keyword or 'small business'
    if use_google:
        try:
            rows.extend(google_search_places(lat, lon, radius, keyword, zip_code))
        except Exception:
            pass
    if use_osm:
        try:
            rows.extend(osm_search_places(lat, lon, radius, keyword))
        except Exception:
            pass

    seen, out = set(), []
    for row in rows:
        key = (row.get('place_id') or row.get('website') or row.get('name') or '').lower()
        if key and key not in seen:
            seen.add(key)
            out.append(row)

    if mode == 'marketing':
        out = marketing_filter(out, keyword)

    out.sort(key=lambda r: r.get('distance_miles', 999999))
    return out

def expand_topic_queries(mode, topic, zip_code='', area_label=''):
    loc = ' '.join(x for x in [area_label, zip_code] if x).strip()
    t = (topic or '').strip()
    if mode == 'Public Intent Search':
        seeds = [t, f'need {t} {loc}', f'looking for {t} {loc}', f'recommend {t} {loc}', f'best {t} {loc}']
    elif mode == 'Relocation Interest Finder':
        area_term = t or area_label or zip_code
        seeds = [area_term, f'moving to {area_term}', f'relocating to {area_term}', f'best neighborhoods in {area_term}', f'apartments {area_term}', f'homes for sale {area_term}', f'cost of living {area_term}']
    elif mode == 'Demand Signal Scanner':
        service = t
        seeds = [
            f'need a {service} {loc}', f'looking for {service} {loc}', f'best {service} {loc}',
            f'{service} near me {loc}', f'recommend a {service} {loc}', f'{service} quote {loc}',
            f'emergency {service} {loc}', f'{service} estimate {loc}', f'{service} cost {loc}', f'{service} help {loc}'
        ]
    else:
        seeds = [t, f'{t} {loc}', f'{t} group {loc}', f'{t} club {loc}', f'{t} meetup {loc}', f'{t} event {loc}']
    out, seen = [], set()
    for s in seeds:
        s = ' '.join(s.split()).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out

def classify_result_type(title, snippet, link):
    text = f"{title} {snippet} {link}".lower()
    if any(x in text for x in ['event', 'meetup', 'calendar', 'show']):
        return 'event'
    if any(x in text for x in ['forum', 'club', 'facebook', 'reddit', 'group']):
        return 'community'
    if any(x in text for x in ['sale', 'auction', 'listing', 'estate sale', 'for sale', 'for rent']):
        return 'listing'
    if any(x in text for x in ['need', 'looking for', 'recommend', 'moving to', 'relocating to', 'quote', 'estimate', 'cost', 'near me', 'help']):
        return 'public_request'
    return 'web_page'

def intent_score(row):
    text = f"{row.get('title','')} {row.get('snippet','')} {row.get('url','')} {row.get('matched_query','')}".lower()
    score = 0
    keywords = {
        'need': 20, 'looking for': 18, 'recommend': 12, 'quote': 18, 'estimate': 18,
        'cost': 12, 'near me': 14, 'emergency': 20, 'help': 10, 'moving to': 18,
        'relocating to': 18, 'homes for sale': 14, 'apartments': 10,
    }
    for k, v in keywords.items():
        if k in text:
            score += v
    rtype = row.get('result_type', '')
    if rtype == 'public_request':
        score += 20
    elif rtype == 'listing':
        score += 10
    elif rtype == 'event':
        score += 6
    return min(score, 100)

def search_public_topics(mode, topic, zip_code='', area_label='', pages=2, use_google=False, public_pages_only=True, high_intent_only=False):
    queries = expand_topic_queries(mode, topic, zip_code, area_label)
    rows, seen = [], set()
    if use_google and get_google_cse_key() and get_google_cse_cx():
        for q in queries:
            for page in range(max(1, pages)):
                try:
                    r = requests.get('https://www.googleapis.com/customsearch/v1', params={'key': get_google_cse_key(), 'cx': get_google_cse_cx(), 'q': q, 'start': page*10+1, 'num': 10}, timeout=20)
                    r.raise_for_status()
                    data = r.json()
                except Exception:
                    data = {}
                for item in data.get('items', []):
                    link = item.get('link', '').strip()
                    if not link or link.lower() in seen:
                        continue
                    seen.add(link.lower())
                    row = {'title': item.get('title', ''), 'url': link, 'snippet': item.get('snippet', ''), 'matched_query': q, 'result_type': classify_result_type(item.get('title', ''), item.get('snippet', ''), link), 'data_source': 'Google Custom Search API', 'topic': topic}
                    row['intent_score'] = intent_score(row)
                    rows.append(row)
    from bs4 import BeautifulSoup
    for q in queries:
        for page in range(max(1, pages)):
            try:
                r = requests.get(f'https://html.duckduckgo.com/html/?q={quote(q)}&s={page*10}', headers={'User-Agent': USER_AGENT}, timeout=20)
                r.raise_for_status()
            except Exception:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            for result in soup.select('.result'):
                a = result.select_one('.result__title a')
                snippet_el = result.select_one('.result__snippet')
                if not a:
                    continue
                title = a.get_text(' ', strip=True)
                link = a.get('href', '').strip()
                snippet = snippet_el.get_text(' ', strip=True) if snippet_el else ''
                if not link or link.lower() in seen:
                    continue
                seen.add(link.lower())
                row = {'title': title, 'url': link, 'snippet': snippet, 'matched_query': q, 'result_type': classify_result_type(title, snippet, link), 'data_source': 'DuckDuckGo HTML', 'topic': topic}
                row['intent_score'] = intent_score(row)
                rows.append(row)
    if public_pages_only:
        rows = [r for r in rows if r['result_type'] in {'event','community','listing','public_request','web_page'}]
    if high_intent_only:
        rows = [r for r in rows if int(r.get('intent_score', 0)) >= 20]
    rows.sort(key=lambda r: int(r.get('intent_score', 0)), reverse=True)
    return rows
