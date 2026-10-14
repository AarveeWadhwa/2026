# Member 3 Part 4 — Bid Portfolio Report and Action Register

## Purpose

Part 4 completes the Member 3 workflow by turning the integrated bid workspace JSON into a portfolio-level action register and shareable reports.

## Inputs and outputs

Input: JSON produced by `backend.agents.bid_workspace_agent` (`results[]` with analysis, change report and preparation checklist).

Outputs:
- JSON portfolio report with recommendation/risk counts and action register
- CSV action register for spreadsheet review
- Markdown summary for a project report or review meeting

## Run

```bash
python3 -m backend.agents.bid_portfolio_report_agent \
  --input outputs/member3_bid_workspace.json \
  --output outputs/member3_portfolio_report.json \
  --csv outputs/member3_action_register.csv \
  --markdown outputs/member3_portfolio_summary.md
```

## Scope and limitations

This component summarizes supplied output only. It does not verify tender portal facts, calculate legal eligibility, predict winning probability, poll for updates, or send notifications. Action detection depends on recognizable checklist fields and statuses; users should review the original tender documents and all generated flags.
