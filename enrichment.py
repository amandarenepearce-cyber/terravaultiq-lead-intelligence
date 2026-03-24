import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})')
HEADERS = {'User-Agent': 'lead-intelligence-engine-v3/1.0'}

def normalize_url(url):
    if not url:
        return ''
    url = url.strip()
    return url if url.startswith(('http://', 'https://')) else 'https://' + url

def fetch_html(url, timeout=8):
    try:
        r = requests.get(normalize_url(url), headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        if 'text/html' not in r.headers.get('Content-Type', ''):
            return '', ''
        return r.text, r.url
    except Exception:
        return '', ''

def enrich_rows(rows):
    out = []
    for row in rows:
        if 'website' not in row or not row.get('website'):
            out.append(row)
            continue
        html, final_url = fetch_html(row.get('website', ''))
        soup = BeautifulSoup(html, 'html.parser') if html else None
        emails = sorted(set(EMAIL_RE.findall(html))) if html else []
        contact_page = ''
        if soup:
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                txt = (a.get_text(' ', strip=True) or '').lower()
                if 'contact' in href.lower() or 'contact' in txt:
                    full = urljoin(final_url or normalize_url(row['website']), href)
                    if urlparse(full).netloc == urlparse(final_url or normalize_url(row['website'])).netloc:
                        contact_page = full
                        break
        row = dict(row)
        row['public_email'] = row.get('public_email', '') or (emails[0].lower() if emails else '')
        row['contact_page'] = contact_page
        row['website_title'] = soup.title.text.strip() if soup and soup.title and soup.title.text else ''
        row['website_status'] = 'ok' if html else 'unreachable'
        out.append(row)
    return out
