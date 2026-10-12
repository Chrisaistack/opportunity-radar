# Opportunity Radar — £0 research prototype

**Status checked 12 October 2026:** the API is reachable, but the official
[planning-application dataset](https://www.planning.data.gov.uk/dataset/planning-application)
lists **0 records and no data providers**. Live queries since 1 October 2026 and
1 May 2025 both returned zero records. This is not currently a working lead feed.
The source covers England, not the whole UK. A scheduled run can check for future
data availability, but cannot create opportunities from an empty dataset.

No paid services, API keys, customer accounts, payments, or sales outreach are used.
Python 3.12 or later is sufficient; there are no third-party Python dependencies.

## Run locally

```sh
python -m unittest discover -s tests -v
python radar.py --demo --output demo-output
python radar.py --since 2026-10-01 --limit 1000
```

The normal run writes `output/report.html`, `output/signals.csv`, and `output/run.json`.
The default date is 30 days before execution. Limits must be 1–1000 records;
requests paginate in batches of up to 100. Reaching the chosen limit is flagged in
run metadata: this is bounded sampling, not a guarantee of complete collection.
An HTTP failure or malformed response fails the run; fictional data is used only
with `--demo`. Run metadata states whether the source is live or fictional.
Existing output files may remain after a failed local run: always check the exit
status and `collected_at_utc` before relying on a report.

## Weekly GitHub collection at £0

Use a **public repository** with `.github/workflows/prototype.yml` on the default
branch. The job refuses to execute for a private repository. It uses a standard
Ubuntu runner, no cache, no paid integrations, and no uploaded Actions artifacts.
Results and collection metadata appear in the Actions run summary; there is no
hosted public website or customer delivery service.

The workflow can be started manually and is scheduled on Mondays at 08:18 UTC
(09:18 during British Summer Time; 08:18 during GMT). Scheduling is best effort;
GitHub may delay runs and disables scheduled workflows in inactive public repos
after 60 days. The first successful manual run must be verified after upload.
Only tests, data collection, and a run summary execute. No messages are sent.

[GitHub billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
states standard runners are free in public repositories and run summaries/logs do
not count toward artifact storage. Do not switch to paid runners, enable paid
services, or add artifact storage without reviewing costs and obtaining approval.

## What changed from the starter

- Added pagination instead of silently capping every request at 100 records.
- Rejects malformed API responses instead of treating them as empty success.
- Validates date and collection limits before making requests.
- Adds run metadata, limit warnings, source attribution, and an empty-results explanation.
- Expanded tests from three to eight, including pagination and error handling.
- Uses a run summary instead of artifact uploads to avoid storage billing.

## Limitations and next work

Keyword scores are unverified research signals, not contracts or qualified leads.
Substring matching can produce false positives. Records are not deduplicated
across runs; there is no region filter or handling of amendments/cancellations.
Live non-empty descriptions and field mapping could not be validated because the
dataset is empty. Pagination is unit-tested, not demonstrated against a non-empty
live dataset. One unfiltered sample request timed out.

To produce useful opportunities, select a region and verify an alternative source
with actual application descriptions, reuse terms, stable identifiers, and dates.
Then add source-specific integration tests, geography filtering, deduplication,
and human review. No additional sources are integrated yet.

## Source and licence

[Planning Data API documentation](https://www.planning.data.gov.uk/docs) documents
the `start_date_year`, `start_date_month`, `start_date_day`, `start_date_match=since`,
`limit`, and `offset` parameters used here. The specification is still developing.

Planning Data attribution: © Crown copyright and database right 2026.
Contains public sector information licensed under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
Demo fixtures are fictional. The data licence does not grant a licence to this
project's code; no code licence has been chosen by the owner.
