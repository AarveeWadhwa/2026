"""Command-line entry point for Member 2's tender assessment pipeline."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
from backend.services.tender_assessment_pipeline import TenderAssessmentPipeline

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assess Member 1 tender extractions against a company profile.")
    parser.add_argument("--company", required=True, help="Path to company profile JSON.")
    parser.add_argument("--tenders", required=True, help="Path to Member 1 extraction JSON or envelope.")
    parser.add_argument("--output", default="outputs/member2_assessment.json", help="Output JSON path.")
    args = parser.parse_args(argv)
    try:
        company = json.loads(Path(args.company).read_text(encoding="utf-8"))
        tenders: Any = json.loads(Path(args.tenders).read_text(encoding="utf-8"))
        result = TenderAssessmentPipeline().assess(company, tenders)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Assessed {result['assessed_tender_count']} tender(s); report written to {output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
