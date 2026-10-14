# Persistent Action Register

The Action Register is a SQLite-backed task module, not just a display of pipeline recommendations.

## Connected agent roles

- **Tender Discovery** creates a source-verification task.
- **Requirement Extraction** creates a requirement-validation task.
- **Eligibility** creates tasks for checks that are not explicitly passed.
- **Compliance / Document** creates tasks for missing or uncertain documents.
- **Bid Analysis** turns emitted analysis action items into tasks.
- **Deadline & Corrigendum** creates a deadline/corrigendum verification task and additional tasks for detected snapshot changes.
- **Bid Preparation** turns checklist entries into tasks.
- **Replanning Engine** creates a high-priority task when a material snapshot change triggers the closed-loop rerun.

## Persistence and task lifecycle

Tasks use the same local SQLite database as tender and preference memory, but separate tables. Agent-generated task identities are deterministic within a company profile and tender, so each analysis refreshes the generated description/priority/dependencies without creating duplicates. It deliberately does **not** overwrite human-managed status, assignee, due date, or notes. Manual tasks can be created in the UI. Status transitions, creation, and edits are written to `action_task_events` for a simple audit trail. Company profiles are isolated by a stable hash of company name, industry, and location.

Statuses: `open`, `in_progress`, `blocked`, `done`, `cancelled`. Priorities: `low`, `medium`, `high`, `urgent`.

## API

- `GET /api/actions` — list tasks; supports `company_name`, `industry`, `location`, `status`, `tender_id`, and `agent_key` query parameters.
- `POST /api/actions` — create a manual task (or explicitly agent-attributed task).
- `PATCH /api/actions/{task_id}` — update title, description, priority, status, assignee, due date, or notes.
- `GET /api/actions/{task_id}/history` — inspect task audit events.

The run endpoint synchronizes tasks after the seven-agent workspace and closed-loop replanning run. Replanning tasks are generated only when a material change is detected. Dependencies are stored as workflow-stage hints, not a hard task-blocking engine. No email, SMS, calendar integration, or cross-user collaboration is implied. Human review remains necessary, especially for official tender/corrigendum evidence.


## Independent Action Register workspace

The sidebar's Action Register entry opens a dedicated workspace instead of leaving the full task list at the bottom of the dashboard. The dashboard scrolls within the main workspace; the Action Register is shown as its own view, and its task list has a bounded, independently scrollable region. The task creation form, filters, export, history, persistent SQLite records, agent synchronization, and replanning integration remain in place. Use **Back to dashboard** to return to the overview.
