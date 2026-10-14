# Member 2 — Part 2: Evidence-aware eligibility and compliance

## Purpose
This overlay extends Member 2's existing starter module. It is designed to accept either the original Member 1 extraction structure or the `normalized_requirements` structure produced by Member 1's later work.

## Changes
- Expanded `TenderRequirements` to include EMD, tender fee, deadline, technical requirements, evidence, and review flags.
- Added an extraction adapter that reads normalized fields while retaining backward compatibility with older keys.
- Eligibility results carry supporting evidence when available and keep missing/unreliable facts as `UNKNOWN`.
- Compliance results accept document inventory entries as filenames or records with `status`, `expiry_date`, and `source`.
- Conservative document matching reduces false positives from very short partial names.
- Added `BidReadinessAgent` to combine eligibility and document compliance into one report with action items.

## Run tests
From the shared repository root:
```bash
python3 -m unittest discover -s tests -v
```

## Integration
```python
from backend.agents.bid_readiness_agent import BidReadinessAgent

report = BidReadinessAgent().evaluate(company_profile_dict, member1_extraction_dict)
```

## Interpretation
- `POTENTIAL_GAPS` means one or more checked criteria did not meet a known threshold; it is not a legal ruling.
- `NEEDS_REVIEW` means some facts are missing or extraction review is needed.
- `FOUND_UNVERIFIED` means a matching inventory record exists but its validity is not established.
- `READY_FOR_HUMAN_REVIEW` is not permission to submit automatically; a human must validate source clauses and files.
