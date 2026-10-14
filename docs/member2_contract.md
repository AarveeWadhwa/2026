
# Member 2 Integration Contract

## Company profile
Use `CompanyProfile.from_dict(profile_dict)` to validate and normalize profile data.

```python
from backend.models.company import CompanyProfile
company = CompanyProfile.from_dict({
    "company_name": "Demo IT Solutions",
    "location": "Pune, Maharashtra",
    "annual_turnover_inr": 14_000_000,
    "years_experience": 4,
    "certifications": ["ISO 9001"],
    "available_documents": ["PAN.pdf", "GST certificate.pdf"]
})
```

## From Member 1's requirement extractor
Member 1 emits strings such as `₹1 crore`, `3 years`, `Maharashtra`, and a list of documents. Convert the output with:

```python
from backend.models.tender import TenderRequirements
requirements = TenderRequirements.from_extraction(extraction_output)
```

Then use normalized values with `EligibilityAgent`:

```python
from backend.agents.eligibility_agent import EligibilityAgent
result = EligibilityAgent().evaluate(company, requirements)
```

And check documents:

```python
from backend.agents.compliance_agent import ComplianceAgent
result = ComplianceAgent().evaluate(extraction_output["documents_required"], company)
```

## Status semantics
- `PASS`: known company value meets a known requirement.
- `FAIL`: known company value does not meet a known requirement.
- `UNKNOWN`: source/profile data is missing or ambiguous; human review needed.
- Document `AVAILABLE` means a likely inventory/filename match only, not proof that the document is valid.

## Notes
- Money parsing supports numeric amounts and common INR units such as lakh/crore. Ambiguous or unrecognized formats return `None`.
- Location checks are conservative because a tender's delivery location is not necessarily a bidder-location restriction.
- Keep original tender clauses and source documents available for human review.
