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
    return {'entity': entity, 'reference': str(rec.get('reference') or ''),
            'description': str(rec.get('description') or rec.get('name') or '')[:800],
            'submitted': str(rec.get('start-date') or ''), 'trade_matches': ', '.join(hits),
            'signal_terms': ', '.join(sorted(set(x for vals in hits.values() for x in vals))),
            'commercial_context': ', '.join(commercial_terms), 'score': score,
            'source_url': url, 'status': 'Unverified early-stage signal; not a confirmed contract'}

def render(items, path, since, demo):
    rows = []
    if not items:
        rows.append('<tr><td colspan="8">No candidate signals in this run. This does not establish an absence of planning applications or work opportunities. Check run.json for the number of source records processed.</td></tr>')
    for item in items:
        rows.append('<tr>' + ''.join('<td>' + (f'<a href="{html.escape(item[k], quote=True)}">Source</a>' if k=='source_url' else html.escape(str(item[k]))) + '</td>' for k in ('score','submitted','reference','description','trade_matches','commercial_context','status','source_url')) + '</tr>')
    body = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Opportunity Radar — research report</title><style>body{{font:16px system-ui,sans-serif;margin:3rem auto;max-width:1150px;padding:0 1rem;color:#17202a}}table{{border-collapse:collapse;width:100%}}th,td{{padding:12px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}}th{{background:#edf3f7}}.note{{padding:1rem;background:#fff4df;border-left:4px solid #bd7d14}}@media(max-width:700px){{table{{display:block;overflow-x:auto}}}}</style><h1>Opportunity Radar</h1><p>Research report · since {html.escape(since)} · {len(items)} candidate signals</p><p class="note">{'DEMO: All entries are fictional. ' if demo else ''}Not verified commercial leads. Planning application coverage is incomplete. Check original source and project scope before contacting anyone. Scores are heuristic and do not establish commercial value, contract availability or accuracy.</p><table><thead><tr><th>Score</th><th>Submitted</th><th>Reference</th><th>Description</th><th>Trades</th><th>Context</th><th>Qualification</th><th>Source</th></tr></thead><tbody>{''.join(rows)}</tbody></table></html>'''
    body += '<footer><p>Source: <a href="https://www.planning.data.gov.uk/dataset/planning-application">Planning Data, England</a>. Contains public sector information licensed under the <a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">Open Government Licence v3.0</a>. Crown copyright and database right. Demo records are fictional.</p></footer>'
    path.write_text(body, encoding='utf-8')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--demo',action='store_true',help='Use fictional local fixture')
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
    if args.demo:
        entries=json.loads((pathlib.Path(__file__).parent/'sample_data'/'fictional_applications.json').read_text())
    else:
        entries=fetch(args.since,args.limit)
    matched=[x for x in (analyse(rec) for rec in entries) if x]
    matched.sort(key=lambda r:r['score'], reverse=True)
    with (output/'signals.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['entity','reference','description','submitted','trade_matches','signal_terms','commercial_context','score','source_url','status']);writer.writeheader();writer.writerows(matched)
    render(matched,output/'report.html',args.since,args.demo)
    metadata = {'mode': 'fictional-demo' if args.demo else 'live-api',
                'collected_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'since': args.since, 'record_limit': args.limit,
                'records_processed': len(entries), 'signals': len(matched),
                'limit_reached': not args.demo and len(entries) == args.limit,
                'coverage': 'England only; incomplete coverage',
                'source': BASE, 'complete_collection_guaranteed': False}
    (output/'run.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(metadata))
    print(f'Processed {len(entries)} records; {len(matched)} candidate signals; report: {output / "report.html"}')
if __name__=='__main__':main()
