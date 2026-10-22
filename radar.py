#!/usr/bin/env python3
"""Opportunity Radar: early-stage public planning signal monitor.
No AI API key, subscription service, or third-party Python packages required.
"""
import argparse
import csv
import datetime as dt
import html
import json
import pathlib
import time
import urllib.parse
import urllib.request

BASE = 'https://www.planning.data.gov.uk/entity.json'
LONDON = 'https://planningdata.london.gov.uk/api-guest/applications/_search'

def fetch_london(since, limit):
    """Read the public GLA guest API; newest validated applications first."""
    date = dt.date.fromisoformat(since)
    until = dt.datetime.now(dt.timezone.utc).date()
    if date > until or not 1 <= limit <= 1000:
        raise ValueError('Use a past/current date and a limit between 1 and 1000')
    entries, seen, total = [], set(), None
    offset = 0
    while offset < limit:
        size = min(100, limit - offset)
        body = {'size': size, 'from': offset, 'track_total_hits': True,
                'query': {'range': {'valid_date': {'gte': date.strftime('%d/%m/%Y'),
                                                  'lte': until.strftime('%d/%m/%Y')}}},
                'sort': [{'valid_date': 'desc'}, {'id': 'asc'}],
                '_source': ['id', 'lpa_name', 'lpa_app_no', 'description',
                            'valid_date', 'status', 'url_planning_app']}
        req = urllib.request.Request(LONDON, data=json.dumps(body).encode('utf-8'),
              headers={'Content-Type': 'application/json', 'X-API-AllowRequest': 'be2rmRnt&',
                       'User-Agent': 'OpportunityRadar/0.3 (public planning research)'})
        with urllib.request.urlopen(req, timeout=40) as resp:
            payload = json.load(resp)
        if not isinstance(payload, dict) or payload.get('timed_out') or payload.get('_shards', {}).get('failed', 0):
            raise ValueError('London API returned an incomplete response')
        hits = payload.get('hits', {})
        page = hits.get('hits') if isinstance(hits, dict) else None
        count = hits.get('total', {}) if isinstance(hits, dict) else {}
        if not isinstance(page, list) or len(page) > size or not isinstance(count, dict) or count.get('relation') != 'eq' or not isinstance(count.get('value'), int):
            raise ValueError('Unexpected London API response')
        total = count['value']
        for hit in page:
            rec = hit.get('_source') if isinstance(hit, dict) else None
            if not isinstance(rec, dict) or not rec.get('id') or not rec.get('lpa_app_no') or (rec.get('description') is not None and not isinstance(rec['description'], str)):
                raise ValueError('London application missing required identity/description fields')
            validated = dt.datetime.strptime(rec['valid_date'], '%d/%m/%Y').date()
            if not date <= validated <= until:
                raise ValueError('London API returned a record outside the requested dates')
            if rec['id'] in seen:
                continue
            seen.add(rec['id'])
            entries.append({'entity': rec['id'], 'reference': rec['lpa_app_no'],
                            'description': rec.get('description') or '', 'start-date': validated.isoformat(),
                            'borough': rec.get('lpa_name') or '', 'application_status': rec.get('status') or 'Unknown',
                            'source_url': rec.get('url_planning_app') or 'https://planninglondondatahub.london.gov.uk/'})
        offset += len(page)
        if len(page) < size or offset >= total:
            break
        if offset < limit:
            time.sleep(0.25)
    if not entries:
        raise ValueError('London feed returned no applications; check source availability and date range')
    return entries, total
TERMS = {
    'roofing': ['roof', 're-roof', 'reroof', 'rooflight', 'cladding'],
    'hvac': ['ventilation', 'air conditioning', 'air-conditioning', 'extraction', 'heat pump', 'mechanical services'],
    'shopfitting': ['shopfront', 'shop front', 'retail unit', 'restaurant', 'commercial kitchen', 'change of use', 'refurbishment'],
}
COMMERCIAL = ['commercial', 'industrial', 'restaurant', 'shop', 'retail', 'warehouse', 'office', 'hotel', 'pub', 'factory', 'unit']
FIELDS = ['entity', 'reference', 'name', 'description', 'start-date', 'entry-date', 'organisation-entity', 'document-url']

def fetch(since: str, limit: int):
    date = dt.date.fromisoformat(since)
    if not 1 <= limit <= 1000:
        raise ValueError('limit must be between 1 and 1000')
    entries = []
    while len(entries) < limit:
        size = min(100, limit - len(entries))
        q = {'dataset': 'planning-application', 'limit': size, 'offset': len(entries),
             'start_date_year': date.year, 'start_date_month': date.month,
             'start_date_day': date.day, 'start_date_match': 'since'}
        req = urllib.request.Request(BASE + '?' + urllib.parse.urlencode(q), headers={'User-Agent': 'OpportunityRadarPrototype/0.2 (research demo)'})
        with urllib.request.urlopen(req, timeout=25) as resp:
            payload = json.load(resp)
        if not isinstance(payload, dict) or not isinstance(payload.get('entities'), list):
            raise ValueError('Unexpected API response: entities must be a list')
        page = payload['entities']
        if len(page) > size or any(not isinstance(rec, dict) for rec in page):
            raise ValueError('Unexpected API records')
        entries.extend(page)
        if len(page) < size:
            break
        if len(entries) < limit:
            time.sleep(0.25)
    return entries

def analyse(rec):
    src = ' '.join(str(rec.get(k) or '') for k in ('name','description','reference')).lower()
    hits = {trade: [t for t in ts if t in src] for trade, ts in TERMS.items()}
    hits = {trade: matched for trade, matched in hits.items() if matched}
    commercial_terms = [s for s in COMMERCIAL if s in src]
    if not hits:
        return None
    score = min(100, len(commercial_terms)*15 + sum(len(v) for v in hits.values())*20)
    entity = str(rec.get('entity') or '')
    url = f'https://www.planning.data.gov.uk/entity/{urllib.parse.quote(entity)}' if entity.isdigit() else 'https://www.planning.data.gov.uk/'
    candidate = str(rec.get('source_url') or '')
    parsed = urllib.parse.urlsplit(candidate)
    if rec.get('borough'):
        url = 'https://planninglondondatahub.london.gov.uk/'
    if parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password:
        url = candidate
    return {'entity': entity, 'reference': str(rec.get('reference') or ''),
            'description': str(rec.get('description') or rec.get('name') or '')[:800],
            'submitted': str(rec.get('start-date') or ''), 'trade_matches': ', '.join(hits),
            'signal_terms': ', '.join(sorted(set(x for vals in hits.values() for x in vals))),
            'commercial_context': ', '.join(commercial_terms), 'score': score,
            'source_url': url, 'borough': str(rec.get('borough') or ''),
            'application_status': str(rec.get('application_status') or 'Unknown'),
            'status': 'Unverified keyword signal; check planning status and whether work is available'}

def render(items, path, since, demo):
    rows = []
    if not items:
        rows.append('<tr><td colspan="10">No candidate signals in this run. This does not establish an absence of planning applications or work opportunities. Check run.json for the number of source records processed.</td></tr>')
    for item in items:
        rows.append('<tr>' + ''.join('<td>' + (f'<a href="{html.escape(item[k], quote=True)}">Source</a>' if k=='source_url' else html.escape(str(item[k]))) + '</td>' for k in ('score','submitted','reference','borough','application_status','description','trade_matches','commercial_context','status','source_url')) + '</tr>')
    body = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Opportunity Radar — research report</title><style>body{{font:16px system-ui,sans-serif;margin:3rem auto;max-width:1150px;padding:0 1rem;color:#17202a}}table{{border-collapse:collapse;width:100%}}th,td{{padding:12px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}}th{{background:#edf3f7}}.note{{padding:1rem;background:#fff4df;border-left:4px solid #bd7d14}}@media(max-width:700px){{table{{display:block;overflow-x:auto}}}}</style><h1>Opportunity Radar</h1><p>Research report · since {html.escape(since)} · {len(items)} candidate signals</p><p class="note">{'DEMO: All entries are fictional. ' if demo else ''}Not verified commercial leads. Planning application coverage is incomplete. Check original source and project scope before contacting anyone. Scores are heuristic and do not establish commercial value, contract availability or accuracy.</p><table><thead><tr><th>Score</th><th>Submitted</th><th>Reference</th><th>Description</th><th>Trades</th><th>Context</th><th>Qualification</th><th>Source</th></tr></thead><tbody>{''.join(rows)}</tbody></table></html>'''
    body += '<footer><p>Default source: <a href="https://planninglondondatahub.london.gov.uk/">Planning London Datahub</a>, Greater London Authority and London planning authorities. London coverage only; dates are validation dates. Check run.json for source and collection limits. Data quality and borough coverage vary. Demo records are fictional. Reuse rights in original application documents require separate review.</p></footer>'
    body = body.replace('<th>Submitted</th><th>Reference</th>', '<th>Source date</th><th>Reference</th><th>Borough</th><th>Planning status</th>')
    path.write_text(body, encoding='utf-8')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--demo',action='store_true',help='Use fictional local fixture')
    p.add_argument('--source',choices=['london','planning-data'],default='london')
    p.add_argument('--since',default=(dt.date.today()-dt.timedelta(days=30)).isoformat())
    p.add_argument('--limit',type=int,default=100)
    p.add_argument('--output',default='output')
    args=p.parse_args()
    try:
        dt.date.fromisoformat(args.since)
    except ValueError:
        p.error('--since must be a date in YYYY-MM-DD format')
    if not 1 <= args.limit <= 1000:
        p.error('--limit must be between 1 and 1000')
    output=pathlib.Path(args.output);output.mkdir(parents=True,exist_ok=True)
    total = None
    if args.demo:
        entries=json.loads((pathlib.Path(__file__).parent/'sample_data'/'fictional_applications.json').read_text())
    elif args.source == 'planning-data':
        entries=fetch(args.since,args.limit)
    else:
        entries,total=fetch_london(args.since,args.limit)
    matched=[x for x in (analyse(rec) for rec in entries) if x]
    matched.sort(key=lambda r:r['score'], reverse=True)
    with (output/'signals.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['entity','reference','description','submitted','borough','application_status','trade_matches','signal_terms','commercial_context','score','source_url','status']);writer.writeheader();writer.writerows(matched)
    render(matched,output/'report.html',args.since,args.demo)
    metadata = {'mode': 'fictional-demo' if args.demo else 'live-api',
                'collected_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'since': args.since, 'record_limit': args.limit,
                'records_processed': len(entries), 'signals': len(matched),
                'records_without_description': sum(not rec.get('description') for rec in entries),
                'limit_reached': not args.demo and (total > len(entries) if total is not None else len(entries) == args.limit),
                'matching_source_records': total,
                'coverage': 'Fictional demo' if args.demo else ('London only; borough coverage varies' if args.source == 'london' else 'England only; incomplete coverage'),
                'source': LONDON if args.source == 'london' else BASE,
                'date_meaning': 'validation date' if args.source == 'london' else 'start date',
                'complete_collection_guaranteed': False}
    (output/'run.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(metadata))
    print(f'Processed {len(entries)} records; {len(matched)} candidate signals; report: {output / "report.html"}')
if __name__=='__main__':main()
