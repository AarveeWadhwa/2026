# Member 3 — Part 3: Integrated Bid Workspace Pipeline

## Purpose
This layer combines the existing Member 3 agents into one repeatable workflow. For each upstream tender assessment, it produces a bid analysis, optional snapshot-change report, preparation checklist, and notification payloads.

## Inputs
- `assessments`: a JSON list or an object containing `assessments`/`results`. Each assessment needs `tender_id`, `eligibility_result`, and `compliance_result`; an optional `tender` object can include title and deadline.
- `current_snapshots` and `previous_snapshots`: optional lists keyed by `tender_id` or `id`. They are compared only when both snapshots exist for the same tender.

## Run
From the repository root, after extracting the overlay:

```bash
python3 -m unittest discover -s tests -v
python3 -m backend.agents.bid_workspace_agent \
  --assessments examples/assessments.json \
  --current-snapshots examples/current_snapshots.json \
  --previous-snapshots examples/previous_snapshots.json \
  --output outputs/member3_bid_workspace.json
```

The command creates the output directory if needed and writes the combined report as JSON.

## Output
- `analysis`: score, recommendation, strengths, risks, action items, missing documents, and evidence
- `change_report`: changed fields, severities, and human-review flag, when prior/current snapshots are supplied
- `preparation_checklist`: pending tasks derived from the analysis plus general bid controls
- `notifications`: structured alert payloads for important changes

## Boundaries
This is an orchestration layer over supplied JSON. It does not fetch tender portals, run scheduled monitoring, send email/SMS, verify document authenticity, submit bids, or make legal eligibility decisions. Scores are indicative and must be reviewed by a person. Inputs should be sourced from the project's actual upstream agents when integrated; the included example is a test fixture only.
