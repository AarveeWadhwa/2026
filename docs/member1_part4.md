# Member 1 — Part 4: Tender Output Quality Audit

## Purpose
The final Member 1 part adds a deterministic quality audit for the JSON envelope created by `tender_intelligence_agent`. It checks required fields, extraction warnings, deadline format and overdue dates, missing evidence maps, and deadline cross-check flags. It does not change the source output.

## Run
First generate the Part 3 output:

```bash
python3 -m backend.agents.tender_intelligence_agent \
  --profile data/sample_company_profile.json \
  --limit 5 --min-score 0 \
  --output outputs/tender_intelligence.json
```

Then run the audit:

```bash
python3 -m backend.agents.tender_validation_agent \
  --input outputs/tender_intelligence.json \
  --output outputs/tender_quality_audit.json
```

Tests:

```bash
python3 -m unittest discover -s tests -v
```

## Interpret results
Each tender receives `quality_status`, `completeness_score`, issue codes, and `review_required`. Completeness is the percentage of required fields present and non-empty; it is not model confidence, eligibility, legal compliance, or bid-win probability. A human should verify important requirements against the original tender and latest official corrigenda.

## Scope limitations
This works on supplied local JSON and does not scrape portals, fetch updates, or send notifications. The deadline check uses the machine's current date unless a date is supplied in tests. Invalid JSON/envelopes stop with an error.
