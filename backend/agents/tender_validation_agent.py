"""CLI for auditing the Member 1 tender-intelligence JSON output."""
import argparse
import json
from pathlib import Path
from backend.services.tender_quality import validate_envelope

def main() -> None:
    parser = argparse.ArgumentParser(description="Audit completeness and review flags in tender-intelligence output.")
    parser.add_argument("--input", required=True, help="Path to tender_intelligence.json")
    parser.add_argument("--output", required=True, help="Path for the quality audit JSON")
    args = parser.parse_args()
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        report = validate_envelope(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(f"Cannot audit input: {exc}")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Audited {report['audited_count']} tender(s); {report['needs_review_count']} need review; saved {output}")

if __name__ == "__main__":
    main()
