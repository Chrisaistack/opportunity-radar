# Opportunity Radar — free London planning monitor

**Live source verified 22 October 2026:** Planning London Datahub, published by the
Greater London Authority and London planning authorities. A live 30-day query found
5,322 applications; the newest 1,000 yielded 332 unverified keyword matches.
One record lacked a description. Counts change as boroughs update their records.

This initial feed covers **London only**. It does not cover the whole UK.
Applications include residential work and decided cases. A keyword match is not a
qualified lead, available contract, permission to start work, or outreach consent.

## Run

Python 3.12+; no packages, accounts, paid API keys or subscriptions required.

```sh
python -m unittest discover -s tests -v
python radar.py --source london --limit 1000
python radar.py --demo --output demo-output
```

Outputs: `output/report.html`, `output/signals.csv`, `output/run.json`.
The CSV includes borough, council reference, planning status, and the council link.
Dates are **validation dates**, not necessarily submission dates. Default window:
last 30 days. `--since YYYY-MM-DD` changes the start. Records are sorted by newest
validation date, then application ID, and fetched in pages of 100, up to a 1–1000
record limit. Metadata reports the matching source total, missing descriptions,
and whether the collection limit leaves more records unprocessed.

Duplicate IDs are removed within a run. There is no history or deduplication
across weekly reports; recent applications may appear repeatedly. Live source
updates during pagination can change the sample. Complete coverage is not claimed.
The report ranks by keyword score; the collection itself samples newest records,
not the highest scoring records across all London applications.

An empty London feed, timeout, failed shard, invalid schema or out-of-window date
fails the run. Missing descriptions are counted and cannot produce text matches.
No silent fictional fallback is used. After a failed local run, older report files
may remain: inspect exit status and collection timestamp before relying on them.

## Weekly GitHub workflow at £0

Public repository: https://github.com/Chrisaistack/opportunity-radar

Runs Mondays at 08:18 UTC: 09:18 UK during BST, 08:18 during GMT. GitHub may delay
scheduled starts. Public schedules can be disabled after 60 days of inactivity.
Manual dispatch is also available. The job uses standard Ubuntu 24.04, Python
3.12, read-only repository permissions, a ten-minute timeout and no artifact or
cache uploads. It refuses to run in a private repository. No paid service, payment
or outreach is configured.

Results and metadata appear in the Actions run summary. It displays the top 100
matches with borough, reference, status, description and council link. The local
CSV/HTML contains all matches from the bounded collection. The workflow does not
persist the CSV/HTML or create a hosted website.

## Sources and reuse

- GLA overview: https://www.london.gov.uk/programmes-strategies/planning/digital-planning/planning-london-datahub
- Public explorer: https://planninglondondatahub.london.gov.uk/
- Official API documentation: https://www.london.gov.uk/sites/default/files/planninglondondatahub_api_connection_technical_documentation_v1.pdf
- Endpoint: https://planningdata.london.gov.uk/api-guest/applications/_search

The official documentation provides read-only guest access and a public
`X-API-AllowRequest` header value. This is a published access constant, not a
personal API credential. The collector requests only identifiers, descriptions,
validation dates, borough, status and source links; no contact details or geometry.

Attribution: Planning London Datahub, Greater London Authority and London planning
authorities. Data is supplied by applicants and authorities and can contain errors.
Public API access is verified; a blanket licence covering commercial redistribution
of original application documents has not been established. Original documents and
maps may have separate rights. This research prototype sends no outreach and does
not sell or redistribute original documents. Review source-specific reuse terms
before commercial delivery. No code licence has been selected by the owner.

## Legacy feed

`--source planning-data` retains the original England Planning Data integration for
diagnostics. It returned zero applications on 12 October 2026 and was still empty
in the 19 October scheduled run. London is now the default; the legacy feed is
never silently used as a fallback.

## Remaining work

Choose target boroughs/trades, improve commercial relevance beyond substring
matching, exclude unsuitable planning statuses, keep a change history and review
candidates manually. No external messages are sent automatically.
