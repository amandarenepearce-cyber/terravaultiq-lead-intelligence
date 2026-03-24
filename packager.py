from datetime import datetime

def normalize_zip_list(zip_text):
    return [x.strip() for x in zip_text.replace('\n', ',').split(',') if x.strip()]

def build_package_summary(df, package_name, seller_name):
    cols = list(df.columns)
    zips = ', '.join(sorted(set(str(x) for x in df.get('source_zip', [])))) if 'source_zip' in df.columns else ''
    keyword = str(df['search_keyword'].dropna().iloc[0]) if 'search_keyword' in df.columns and len(df['search_keyword'].dropna()) else ''
    return f"""PACKAGE NAME: {package_name}
PREPARED BY: {seller_name}
DATE: {datetime.now().strftime('%Y-%m-%d %H:%M')}
TOTAL LEADS: {len(df)}
SEARCH KEYWORD: {keyword}
SOURCE ZIPS: {zips}
FIELDS INCLUDED: {', '.join(cols)}

NOTES:
- Public business leads and public topic results only
- Review results before resale or outreach
"""
