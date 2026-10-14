# Closed-loop corrigendum replanning

BidPilot's `/api/run` now executes a bounded, change-triggered reprocessing pass when the current normalized tender snapshot differs materially from the company's persisted snapshot.

## Execution behavior

1. Discovery and requirement extraction run for the current configured catalogue.
2. The planner compares each current snapshot with the previous SQLite snapshot.
3. If material fields changed, BidPilot re-runs discovery/requirement extraction from the configured catalogue, re-assesses changed tender records through eligibility/compliance, and re-runs the downstream bid analysis and preparation workspace for those tenders.
4. The rerun outputs replace the affected rows in the final workspace. The API response includes `replanning_execution`, with cycle number, trigger, affected tender IDs, executed stages, status, and rerun count.
5. The updated assessment is persisted for future comparisons. Human review remains required.

## Boundaries

- The loop is deliberately bounded to one replan cycle per API run to avoid infinite execution. A later API run can detect further changes and reprocess again.
- Re-extraction reads the currently configured local catalogue and referenced documents. This is not live portal ingestion; live corrigendum behavior requires a validated source connector/parser that updates those inputs.
- The planner uses explicit rules and dependency mapping, not an unconstrained LLM planner.
- The action register is a generated list of suggested actions; it is not yet a complete task assignment/sign-off system.

## How to verify

Run `python -m unittest tests.test_app -v`. The integration test injects a prior tender snapshot with a material difference and verifies that a replan cycle reports `completed` and reruns extraction and eligibility stages.
