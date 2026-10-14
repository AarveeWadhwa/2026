# Member 1 — Part 3: Tender Intelligence Workflow

## Purpose

This contribution composes the existing `TenderDiscoveryAgent` and `TenderRequirementAgent` into a single runnable workflow. It is designed to provide ranked tenders plus extracted, evidence-backed requirements to the next project stage.

## Run it

From the repository root, prepare a company profile JSON file, for example:

```json
{
  "industry": "IT and computer equipment",
  "services": "computer hardware networking and IT support",
  "keywords": ["laptop", "network", "software", "cybersecurity"],
  "location": "Maharashtra"
}
```

Save it as `data/sample_company_profile.json`, then run:

```bash
python3 -m backend.agents.tender_intelligence_agent \
  --profile data/sample_company_profile.json \
  --limit 5 \
  --min-score 0 \
  --output outputs/tender_intelligence.json
```

## Output contract for Member 2

Each successfully processed result retains Member 1's existing extraction keys at the top level, including `tender_id`, `eligibility`, `certifications`, `documents_required`, `normalized_requirements`, `evidence`, and `warnings`. Discovery-specific metadata is nested under `discovery`. This keeps the result compatible with `TenderRequirements.from_extraction(result)` in Member 2's current starter code.

## Safety and limitations

- Relevance score is lexical overlap, not a legal or eligibility decision.
- A missing document is returned with warnings rather than silently treated as an empty successful extraction.
- Catalogue document paths are constrained to the project root.
- A catalogue/document deadline mismatch is flagged for review.
- Scanned PDFs may need OCR; OCR is not implemented in this module.
- The catalogue is local sample data. Live portal polling, authenticated access, and automatic corrigendum ingestion are not implemented here.
- A human must verify requirements against the official tender and latest corrigenda before any bid decision.
