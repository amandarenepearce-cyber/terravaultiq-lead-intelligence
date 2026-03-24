def score_rows(rows):
    out = []
    for row in rows:
        row = dict(row)
        if 'website' not in row:
            row['lead_score'] = ''
            out.append(row)
            continue
        score = 100
        reasons = []
        if not row.get('website'):
            score -= 35; reasons.append('no website')
        if row.get('website_status') == 'unreachable':
            score -= 25; reasons.append('website unreachable')
        if not row.get('public_email'):
            score -= 8; reasons.append('no public email')
        if not row.get('contact_page'):
            score -= 6; reasons.append('no contact page')
        if not row.get('website_title'):
            score -= 6; reasons.append('missing website title')
        try:
            rating = float(row.get('rating'))
            if rating < 4.0:
                score += 8; reasons.append('low rating opportunity')
        except Exception:
            pass
        try:
            reviews = int(row.get('review_count'))
            if reviews < 20:
                score += 10; reasons.append('low review count opportunity')
        except Exception:
            pass
        row['lead_score'] = max(0, min(100, score))
        row['score_reasons'] = '; '.join(reasons)
        row['marketing_prospect'] = 'yes' if row['lead_score'] >= 65 else 'maybe' if row['lead_score'] >= 45 else 'no'
        out.append(row)
    return out
