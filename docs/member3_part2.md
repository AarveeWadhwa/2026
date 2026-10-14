# Member 3 — Part 2: Evidence-aware bid analysis and change monitoring

## What changed
- Snapshot-based deadline/corrigendum comparison produces field-level change events with severity.
- Bid analysis consumes Member 2 eligibility/compliance report shapes, reports strengths, risks, evidence, and prioritized actions.
- Preparation agent produces a checklist with general controls plus specific analysis/compliance actions.
- Notification service creates payloads for high-priority tender changes and deadline reminders; it does not send email/SMS by itself.
- Reports explicitly distinguish analysis from verified facts and retain human-review requirements.

## Run tests
From the shared repository root:
```bash
python3 -m unittest discover -s tests -v
```

## Example
```python
from backend.agents.deadline_agent import DeadlineAgent
from backend.agents.bid_analysis_agent import BidAnalysisAgent
from backend.agents.preparation_agent import PreparationAgent

changes = DeadlineAgent().compare_snapshots(old_snapshot, new_snapshot)
analysis = BidAnalysisAgent().analyze(tender_id, eligibility_report, compliance_report, changes)
checklist = PreparationAgent().prepare(tender_id, analysis, compliance_report, deadline)
```

## Boundaries
This package compares snapshots supplied by a caller. It does not poll tender portals, guarantee that every corrigendum has been captured, or send notifications without a delivery adapter. All official tender conditions and deadlines must be verified against the source.
