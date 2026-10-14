
# Member 1 Integration Contract

## Tender discovery input

```python
profile = {
    "industry": "IT services",
    "services": "software development and network support",
    "keywords": ["cybersecurity", "web development"],
    "location": "Pune, Maharashtra",
    "past_projects": ["municipal website"]
}
```

Call:
```python
from backend.agents.discovery_agent import TenderDiscoveryAgent
matches = TenderDiscoveryAgent().search(profile, limit=10, min_score=0)
```

Each result includes the original tender fields plus `relevance_score`, `matched_terms`, and `discovery_note`.

## Requirement extraction input

```python
from backend.agents.requirement_agent import TenderRequirementAgent
requirements = TenderRequirementAgent().extract(tender_text, tender_id="BP-2026-001")
```

The result is JSON-serializable and intended as input to Member 2's eligibility and compliance agents.

## Important limitations

- Sample tender records are fictional demo data; the `example.gov.in` links are placeholders, not real tenders.
- Current matching is keyword-based and should not be described as semantic AI ranking.
- Rule-based extraction can miss table content, scanned PDFs, unusual date formats, and nuanced legal language.
- Scanned PDFs need OCR, which is not included in this starter.
- A human must verify source documents and corrigenda before submitting a bid.
