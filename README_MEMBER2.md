
# BidPilot AI — Member 2: Eligibility & Compliance

This module owns company-profile validation, tender eligibility checks, and required-document matching.

## Files
- `backend/models/company.py` — normalized company profile model and validation
- `backend/models/tender.py` — requirement schema used by the eligibility/compliance modules
- `backend/agents/eligibility_agent.py` — compares company facts with tender requirements
- `backend/agents/compliance_agent.py` — compares available company documents with requested tender documents
- `tests/test_eligibility.py` and `tests/test_compliance.py` — unit tests
- `docs/member2_contract.md` — integration notes for the team

## Setup
Copy these files into the shared BidPilot repository, preserving existing files from Members 1 and 3. The code uses only the Python standard library.

Run tests from the shared repository root:
```bash
python -m unittest discover -s tests -v
```

## Important
This module produces preliminary decision support. It must not represent an unclear or missing value as a definite failure, and it does not replace human review of the tender documents. A missing document is marked missing; it does not automatically mean the company is legally ineligible.
