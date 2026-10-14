# Reviewer feedback, changes made, and remaining gaps

## Review comment: fixed pipeline with no revisiting or replanning

**Change made:** added `backend/agents/replanning_agent.py`. It compares prior and current normalized tender snapshots and flags material changes to deadlines, EMD, eligibility thresholds, certifications, required documents, and technical requirements. Its output specifies why a replan is required and which workflow stages should be revisited. Replanning flags are included in `/api/run` and surfaced as high-priority Action register items. The application reruns extraction and eligibility/compliance assessment on every run.

**Remaining gap:** the policy is deterministic and triggered by snapshots already available to the application. It does not autonomously poll portals, fetch corrigenda, or dynamically invoke arbitrary agent graphs. A changed tender will be handled only after its changed version reaches the system.

## Review comment: no memory across multiple tender cycles

**Change made:** added `backend/services/tender_memory.py`, using SQLite to persist per-company/per-tender snapshots, latest assessment summaries, first/last observed timestamps, and cycle counts. On subsequent `/api/run` calls, the service loads history and compares it to current snapshots. `GET /api/memory` exposes a summary, and `DELETE /api/memory` clears the selected company's records.

**Remaining gap:** memory is local to the installation and based on a company identity composed of company name, industry, and location. It does not yet use shared cloud storage, long-term preference learning, or automatic ranking adaptation.

## Other known project weaknesses / scope limits

- The default tender catalogue contains fictional/local sample records, not live government procurement data.
- No scheduled polling or automatic corrigendum download is configured.
- Requirement extraction is rule-based and can miss or misclassify complex clauses; evidence must be checked against official source documents.
- The document inventory comparison is not document authenticity verification.
- Notifications are generated as structured payloads; no actual email/SMS/push delivery is configured.
- Human-in-the-loop is represented by review flags and required-review metadata, not a complete authenticated approval/sign-off workflow.
- Scores are heuristic readiness indicators, not probabilities of winning or legal conclusions.
- SQLite memory is single-installation local storage; production deployment needs access control, retention policy, backup, and secure multi-user storage.

The project should be described as a multi-agent tender intelligence and bid-readiness prototype with rule-based extraction, snapshot-based monitoring, change-triggered replanning, and persistent local memory—not as a fully autonomous production procurement service.
