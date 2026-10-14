
# BidPilot AI — Member 3: Bid Analysis, Monitoring & Preparation

This module combines eligibility and compliance outputs into a bid decision-support report, tracks deadline/corrigendum changes, and drafts a bid-readiness checklist.

## Included
- `backend/agents/bid_analysis_agent.py` — transparent weighted readiness scoring and recommendation
- `backend/agents/deadline_agent.py` — deadline parsing and change/corrigendum comparison
- `backend/agents/preparation_agent.py` — human-review bid readiness report and action list
- `backend/services/notification_service.py` — simple alert-message formatter (no external notifications)
- `backend/models/report.py` — report structure
- tests and integration contract

This version runs locally with Python's standard library only. Monitoring is comparison-based: the agent compares a newly fetched tender record with a previously saved record. Scheduling and live tender-portal polling are integration tasks, not silently simulated.

## Run demos
From this folder:
```bash
python -m backend.agents.bid_analysis_agent
python -m backend.agents.deadline_agent
python -m backend.agents.preparation_agent
python -m unittest discover -s tests -v
```

## Integration
Member 3 expects Member 2's eligibility result (`outcome`, `eligibility_score`, `checks`, `failed_checks`, `unknown_checks`) and compliance result (`document_readiness_score`, `checklist`, `missing_count`).

A score is decision support only, not a guarantee of tender success. All generated bid content must be reviewed and approved by a human before submission.
