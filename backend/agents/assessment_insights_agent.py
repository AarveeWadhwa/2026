"""CLI for Member 2 portfolio assessment insights."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from backend.services.assessment_insights import AssessmentInsights

def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize tender assessment status and priority actions.")
    parser.add_argument("--input", required=True, help="Member 2 assessment JSON")
    parser.add_argument("--output", default="outputs/member2_insights.json")
    args = parser.parse_args()
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(source, dict): parser.error("Input must be a JSON object")
    result = AssessmentInsights().build(source)
    target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Summarized {result['tender_count']} tender(s); saved {target}")

if __name__ == "__main__": main()
