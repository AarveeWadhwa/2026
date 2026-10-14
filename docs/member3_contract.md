
# Member 3 Integration Contract

## Inputs from Member 2

`EligibilityAgent.evaluate(...)` returns an object containing `company_name`, `tender_id`, `eligibility_score`, `checks`, `failed_checks`, and `unknown_checks`.

`ComplianceAgent.evaluate(...)` returns `company_name`, `document_readiness_score`, `missing_count`, and `checklist`.

## Example orchestration

```python
from backend.agents.bid_analysis_agent import BidAnalysisAgent
from backend.agents.deadline_agent import DeadlineCorrigendumAgent
from backend.agents.preparation_agent import BidPreparationAgent

analysis = BidAnalysisAgent().analyze(
    eligibility_result=eligibility_result,
    compliance_result=compliance_result,
    tender=tender_record,
)
change_result = DeadlineCorrigendumAgent().compare(previous_tender, latest_tender)
report = BidPreparationAgent().prepare(
    analysis,
    tender=tender_record,
    compliance_result=compliance_result,
)
```

Use `format_tender_alert(change_result)` to render a message if `has_changes` is true.

## Scoring and safety
- Default score weights: 65% eligibility and 35% document readiness; configurable.
- The score is a readiness indicator, not a probability of winning.
- Any failed eligibility check or missing required document leads to `ACTION_REQUIRED`.
- Missing/unclear eligibility data leads to `NEEDS_HUMAN_REVIEW`.
- Monitoring compares snapshots supplied by a source adapter; it does not itself poll a live portal.
- A person must verify official documents, changes, deadlines, and final bid content.
