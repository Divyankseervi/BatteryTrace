# Claude work plan and first sprint

## Sprint 1 — inspect and stabilize
1. Run existing test suite; note actual results.
2. Add a `docs/CURRENT_STATE_AUDIT.md` documenting routes, schema, domain workflows, test coverage, dependencies and security concerns.
3. Add explicit tests for invalid lifecycle transitions, date validation, passport chain rules, partial rollback, repeated submissions and relationship transfer.
4. Fix defects discovered by tests before changing the interface.

## Sprint 2 — lifecycle domain model
1. Centralize lifecycle event types and allowed transitions.
2. Implement valid passport version linking and cycle prevention.
3. Implement component-transfer operations with temporal boundaries and audit notes.
4. Add constraints and transaction tests; include a migration/reset story.

## Sprint 3 — recall engine
1. Build deterministic generator with fixed seed and known ground truth.
2. Add forward/backward lineage and downstream recall reports.
3. Add completeness/false-positive/false-negative counters for synthetic test cases.
4. Export results and include a concise method note.

## Sprint 4 — visual and interaction pass
1. Audit current UI before redesign; create a small reusable design system.
2. Make the dashboard resemble a serious engineering operations tool.
3. Add responsive layouts, accessible table interactions, inline validation, event detail and loading/error/empty states.
4. Test on desktop, tablet and phone sizes.

## Sprint 5 — controlled database comparison
1. Decide and document relational target (PostgreSQL strongly preferred for comparison) and graph target (Neo4j).
2. Use one generated canonical dataset and stable identifiers.
3. Implement equivalent query semantics and correctness tests.
4. Benchmark multiple runs and save raw results with environment metadata.

## Sprint 6 — final-year handoff
- Migrations, environment example, clean start instructions, reproducible tests, architecture diagram, ERD, database data dictionary, short viva deck/script, limitations, and next work.

## Important execution rule
This work plan is not a reason to stop and ask the user what to do. Start with Sprint 1, finish complete vertical slices, and make sensible bounded decisions. If a full sprint cannot fit in one session, deliver the completed changes, tests, and exact next step; don't claim incomplete work is done.
