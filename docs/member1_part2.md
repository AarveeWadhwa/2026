# Member 1 — Part 2: Evidence-backed requirement extraction

## What this contribution adds

- Extracts tender text from TXT, Markdown, PDF, and DOCX files. DOCX table rows are included in the extracted text.
- Captures source filename, file type, character count, SHA-256 fingerprint, PDF page count, and extraction warnings.
- Retains evidence snippets for turnover, experience, location, deadline, EMD, tender fee, certifications, documents, technical requirements, and evaluation criteria.
- Adds `normalized_requirements` to the existing output contract, with amounts normalized to INR, experience normalized to months, and supported dates normalized to ISO `YYYY-MM-DD`.
- Adds explicit review flags and warnings; extracted values are candidates, not authoritative interpretations.
- Adds a CLI option to save output JSON to a file.

## Run

```bash
pip install -r requirements.txt
python -m backend.agents.requirement_agent data/sample_tenders/tender_001.txt
python -m backend.agents.requirement_agent data/sample_tenders/tender_001.txt --output outputs/tender_001_requirements.json
python -m unittest discover -s tests -v
```

PDF and DOCX support:

- `pypdf` extracts selectable PDF text; it does not OCR scanned images. The parser warns when pages yield no text.
- `python-docx` extracts DOCX paragraphs and tables.

## Downstream interface for Member 2

Existing fields remain available (`eligibility`, `financial_requirements`, `documents_required`, `certifications`, `deadlines`, `evidence`, `warnings`). Member 2 can use `normalized_requirements` for numeric comparisons:

- `minimum_annual_turnover_inr`
- `minimum_experience_months`
- `emd_inr`
- `tender_fee_inr`
- `bid_submission_deadline_iso`

Missing or unparseable fields remain `null`; they must not be interpreted as zero or as proof that no requirement exists. Keep `review_required: true` until a person has checked the original tender and all amendments.

## Current limitations

This is a deterministic rule-based extractor, not a trained LLM. It may miss requirements in complex tables, images, annexures, scanned PDFs, unusual wording, or clauses that qualify a general rule. No live tender portal is scraped by this module. For production use, add OCR, portal-specific approved adapters, and reviewed test documents with expected outputs.
