# Adaptive Monitoring and Company Memory

## Implemented in this build

- SQLite persistence for tender snapshots and assessment summaries across runs.
- Rule-based replanning for material changes to monitored fields.
- Configurable HTTPS source polling and content fingerprinting.
- Persisted monitor change events and a status API.
- Explicit company feedback stored across sessions.
- Transparent keyword weights and ranking nudges derived from feedback.
- Dashboard controls for a manual source check and preference feedback.
- Importable n8n schedule workflow that calls the monitor endpoint every 30 minutes.

## Deliberate boundaries

- Source URLs are not pre-populated with invented endpoints. Configure official sources that permit automated access.
- The generic monitor detects page/feed/document content changes, not the semantic meaning of every corrigendum.
- Each procurement portal needs a tested parser adapter to extract tender IDs, corrected fields, document links, and dates. Only after that adapter updates a normalized snapshot can the existing tender replanner rerun affected stages reliably.
- n8n is a scheduler/orchestrator, not the eligibility reasoning engine.
- Preference adaptation is based on explicit feedback counts and a transparent ranking penalty, not trained ML or hidden user profiling.
- No real email/SMS is sent by this module. Notifications require a configured provider and credentials.

## Validation

Unit tests use injected fetch functions to test baseline creation, change detection, unchanged sources, HTTPS validation, company scoping, and feedback-based preference profiles without depending on live websites.
