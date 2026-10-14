"""CLI wrapper for the integrated Member 3 bid workspace pipeline."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from backend.services.bid_workspace_pipeline import BidWorkspacePipeline, load_json_list


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bid analysis, change reports, and preparation checklists from JSON inputs.")
    parser.add_argument("--assessments", required=True, help="JSON list or object with results[] containing tender assessments")
    parser.add_argument("--current-snapshots", help="Optional JSON list of current tender snapshots")
    parser.add_argument("--previous-snapshots", help="Optional JSON list of previous tender snapshots")
    parser.add_argument("--output", default="outputs/member3_bid_workspace.json")
    args = parser.parse_args()
    assessments = load_json_list(args.assessments, "assessments")
    current = load_json_list(args.current_snapshots) if args.current_snapshots else []
    previous = load_json_list(args.previous_snapshots) if args.previous_snapshots else []
    result = BidWorkspacePipeline().run(assessments, current, previous)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Processed {result['assessment_count']} assessment(s); saved {output_path}")


if __name__ == "__main__":
    main()
