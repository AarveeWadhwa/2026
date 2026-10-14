# BidPilot AI — Integrated Tender Intelligence Workspace

BidPilot AI combines the work packages from all three team members into one local web application. It connects the existing discovery, requirement extraction, eligibility, compliance, bid analysis, deadline-snapshot comparison, preparation checklist, quality audit, and portfolio reporting modules to a browser dashboard.

## Start on macOS

**Option A — one command**

```bash
cd /path/to/BidPilot_Integrated
./run_mac.command
```

Open **http://127.0.0.1:8000** in your browser. The launcher installs the dependencies from `requirements.txt` if FastAPI/Uvicorn are missing.

**Option B — manual setup (recommended for a reproducible environment)**

```bash
cd /path/to/BidPilot_Integrated
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Stop the server with `Ctrl+C`.

## What is connected

1. **Member 1 — Discovery & extraction:** ranks local catalogue records against the company profile, parses referenced tender text/PDF/DOCX where supported, extracts requirements and evidence, and emits a quality audit.
2. **Member 2 — Eligibility & compliance:** compares normalized tender requirements with the company profile and document inventory, records unknowns/missing items, and summarizes portfolio-level review actions.
3. **Member 3 — Bid analysis & preparation:** combines upstream assessment records into readiness indicators, checklists, and notification payloads; the reporting layer exports portfolio/action-register summaries.
4. **Frontend:** editable company profile, end-to-end analysis button, metric cards, searchable tender table, eligibility/compliance checks, action register, detail modal, and JSON export.

## API

- `GET /api/health` — service health.
- `GET /api/sample-company` — sample company profile.
- `GET /api/tenders` — local tender catalogue.
- `POST /api/run` — run the integrated workflow. Accepts an optional JSON object such as:

```json
{
  "company": {
    "company_name": "Demo IT Solutions",
    "industry": "IT services",
    "location": "Pune, Maharashtra",
    "annual_turnover_inr": 14000000,
    "years_experience": 4,
    "certifications": ["GST", "PAN", "ISO 9001"],
    "available_documents": ["PAN.pdf", "GST Registration Certificate.pdf"],
    "keywords": ["laptop", "network", "software"]
  },
  "limit": 10,
  "min_score": 0
}
```

- `POST /api/audit` — audit a supplied Member 1 result envelope.
- OpenAPI docs: `http://127.0.0.1:8000/docs`.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests cover the existing agent/service modules plus the Member 2 assessment-insights summary. A separate API smoke test is included for health and the integrated pipeline.

## Important scope and honest limitations

- The bundled catalogue and tender documents are **fictional sample data** intended for a project demo. The default mode is `local_catalogue`.
- Keyword overlap and rule-based extraction are explainable baselines, not a trained language model. Extracted requirements may be incomplete or incorrect.
- No live government portal scraping, scheduled polling, automatic corrigendum ingestion, real email/SMS sending, or production authentication is enabled by default.
- Corrigendum monitoring in the included agents compares previous/current snapshots when those snapshots are supplied; the UI's default run does not claim live monitoring.
- Eligibility/readiness scores are indicators, not probability of winning or a legal determination. Humans must verify original tender clauses, document authenticity/expiry, and current corrigenda.
- This is a local development/demo application. Do not expose it publicly without security review, authentication, input controls, logging, and deployment hardening.

## Repository layout

```text
backend/agents/       member agents and CLI entry points
backend/models/       company, tender and report schemas
backend/services/     extraction, assessment, workspace and reporting pipelines
data/                 fictional sample company and tender catalogue/documents
examples/             sample assessment/snapshot payloads for CLI demonstrations
frontend/             dashboard HTML, CSS and JavaScript
outputs/              generated local reports (ignored by Git)
tests/                unit and pipeline tests
```

## Review feedback addressed: replanning and company memory

The original design was largely a one-way pipeline. This version adds two explicit mechanisms:

- **Company-scoped persistent memory:** `backend/services/tender_memory.py` stores a normalized snapshot, latest assessment summary, first/last-seen timestamps, and cycle count per company/tender in a local SQLite database (`data/bidpilot_memory.sqlite3`). Repeated runs can compare the current tender snapshot against the previous observed snapshot. Memory is local to this installation and should be backed up/secured appropriately.
- **Change-triggered replanning policy:** `backend/agents/replanning_agent.py` detects changes in monitored fields such as submission deadline, EMD, eligibility/turnover/experience, required documents, certifications, and technical requirements. It emits `replan_required`, changed fields, rationale, and a list of stages to revisit. These appear in API response `replanning` and the Action register.
- **Reassessment on each run:** every call to `/api/run` reruns discovery, extraction and eligibility/compliance assessment using the currently configured catalogue. The replanning signal indicates which downstream stages need special attention when changes are detected.
- **Memory endpoints:** `GET /api/memory` returns a summary of the default demo company's stored tender history; `DELETE /api/memory` clears that company's memory. Query parameters `company_name`, `industry`, and `location` scope these endpoints.

### Remaining limitations (explicit)

This addresses the review's architecture weaknesses at prototype level, but it is not a fully autonomous multi-agent planning engine yet. The replanning policy is deterministic and field-based; it does not use an LLM planner, dynamically execute arbitrary agent graphs, or automatically retrieve corrigenda. It can only detect a change after a new/current snapshot is available. The current catalogue is local sample data, so there is no live scheduled portal polling. Company memory is SQLite on one machine, not shared cloud memory; it does not yet learn generalized preferences across companies or automatically adapt ranking weights. Human approval is represented through review flags and human-review-required metadata, not a full role-based approval/sign-off system. Extraction is rule-based, notifications are payloads only, and all eligibility conclusions require verification against official documents.

## Reviewer feedback summary

**Strengths retained:** seven distinct agent roles; comparison of tender requirements with company capabilities; explicit missing-item/review flags; and human-in-the-loop decision support.

**Weakness 1 — fixed pipeline:** improved with a change-triggered replanning policy and a visible action-register entry identifying which stages should be revisited. Still rule-based rather than fully autonomous replanning.

**Weakness 2 — no memory across cycles:** improved with persistent company-scoped SQLite history and tender snapshot/assessment cycle counts. Memory only helps compare tenders observed in this installation; it is not a trained long-term preference model.

## Adaptive monitoring, replanning, and preference memory

This build adds configurable HTTPS source polling, persisted content fingerprints/change events, a feedback-based company preference profile, and a starter n8n workflow.

### Configure source monitoring

Edit `data/monitor_sources.json` and add official public HTTPS URLs that permit automated access:

```json
{
  "sources": [
    {"id": "procurement-feed-example", "url": "https://YOUR-OFFICIAL-SOURCE.example/feed.json", "enabled": true, "timeout_seconds": 15}
  ]
}
```

Use an actual official source URL; the example above is deliberately a placeholder. Start the API and call `POST /api/monitor/run` or use the dashboard's **Check sources now** button. The monitor stores a first-observation baseline, then detects changes by content hash. It records change events in SQLite. **A generic content change is not itself a parsed corrigendum:** for each portal, implement and test a source-specific adapter that maps its notices/documents to tender IDs and normalized fields before claiming automatic tender-field updates.

### n8n scheduled workflow

Import `n8n/bidpilot_scheduled_monitor_workflow.json` into n8n and activate it after configuring source URLs. It calls `POST /api/monitor/run` every 30 minutes. If n8n runs in Docker on the same Mac, `host.docker.internal` usually reaches the host API; otherwise change the URL to the reachable API address. The workflow only schedules polling; it does not bypass portal restrictions or parse tender documents itself.

### Preference feedback

The dashboard includes a feedback form. Useful feedback increases keyword preference weights; not-useful feedback creates negative weights. The next analysis uses positive preferences as ranking hints and applies a capped penalty for negative keyword matches. This is transparent feedback-based adaptation, not machine-learning model training, and it never overrides eligibility checks. Feedback is scoped by company name, industry, and location in the local SQLite database.

### Replanning behaviour

When the app receives a new assessment snapshot, the existing replanning policy identifies material changes and the stages that should be revisited. Source monitor change events are persisted for review. The current generic monitor does not automatically convert arbitrary HTML/RSS into normalized tender snapshots; source-specific adapters are needed for that last integration step.

### New endpoints

- `GET /api/monitor/status` — source states and recent change events
- `POST /api/monitor/run` — poll all enabled configured sources once
- `GET /api/preferences?company_name=...&industry=...&location=...` — preference summary
- `POST /api/preferences/feedback` — store explicit preference feedback

Example feedback body:

```json
{
  "company": {"company_name":"Demo IT Solutions","industry":"IT services","location":"Pune, Maharashtra","keywords":["network"]},
  "category":"networking", "keywords":["network","router"], "rating":1,
  "tender_id":"BP-2026-001", "note":"Matches our service focus"
}
```

## Closed-loop corrigendum replanning

When a tender's monitored fields differ from the previously stored SQLite snapshot, `/api/run` now performs a bounded reprocessing pass: it re-runs discovery/requirement extraction from the configured local catalogue, re-runs eligibility and compliance for affected tenders, and re-runs downstream bid analysis/preparation. The API returns `replanning_execution` with the cycle status and stages actually invoked. See `docs/closed_loop_replanning.md`.

This is a rule-based, one-cycle feedback loop. It is not live portal polling by itself: a real corrigendum must first be ingested into the configured source/document data. Human review is still required.

## Persistent Action Register

The Action Register is now a task-management module backed by the same SQLite database used for tender memory. Run analysis to synchronize idempotent tasks from discovery, requirement extraction, eligibility, compliance/document checks, bid analysis, deadline/corrigendum review, bid preparation, and material-change replanning. Existing human status/assignee/due-date/notes are preserved when agent outputs refresh. You can create tasks, update status/priority/owner/due date/notes, inspect edit history, filter by status/agent, and export the task list as JSON.

See [`docs/action_register_task_management.md`](docs/action_register_task_management.md) for its lifecycle, API, and limits. Dependencies are descriptive stage hints, not a full dependency scheduler; notifications and live portal ingestion are not enabled by this module.


The Action Register opens as a separate workspace from the sidebar. Its task list scrolls independently, so a large task backlog does not create an endlessly long dashboard.
