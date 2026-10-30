# BatteryTrace acceptance checklist (status after the v2 iteration)

`[x]` = verified by an automated test or a recorded manual check (evidence named). `[ ]` = NOT done; reason given. Last full run: 102 unit/integration tests passing; 19 browser flows passing (Playwright, headless Chromium).

## Baseline
- [x] `python -m unittest discover -s tests -v` passes from a clean checkout (102 tests).
- [x] First start creates a fresh DB with synthetic data; no database file is bundled (`.gitignore`).
- [x] README has run/reset/test commands for Windows and Linux/macOS.

## Data integrity
- [x] Unique asset codes and passport versions (`DatabaseConstraintTests.test_value_checks`, `test_passport_chain_rules`).
- [x] At most one ACTIVE passport per asset (partial unique index; `test_one_active_passport_index`).
- [x] Passport chain: same asset, earlier version, identity immutable, so no cycle is possible (trigger `trg_passport_chain`, `trg_passport_immutable`; tests above; DQ-004 finds legacy violations).
- [x] Illegal transitions rejected with no partial change (`TransitionTests.assertRejectedUnchanged` snapshots all four tables).
- [x] Repurposing creates one valid linked passport version (`test_repurpose_passport_chain_is_valid`, `test_next_passport_version_skips_existing_versions`).
- [x] Recycling + passport closure + link closure atomic (`test_midway_failure_rolls_back_*`, `test_database_failure_after_event_insert_rolls_everything_back`); repeat submissions: idempotency keys (`IdempotencyTests`, `ConcurrencyTests`).
- [x] Component transfers close the old link and open the new one with an effective date (`TransferTests`).
- [x] Invalid intervals, double parents rejected by trigger/CHECK; legacy conflicts flagged (DQ-002/006) and repairable (`test_close_relationship_repairs_seeded_double_parent`). Cycles are impossible by HierarchyRule; cycle-safe traversal tested on planted cycles.
- [x] Findings show rule id, evidence records, suggested step and the rule's limits (`test_every_issue_has_evidence_and_limits`).

## Recall / lineage
- [x] Up/down traces on linear, branching (shared ancestors), deep (depth limit), disconnected, historical and cyclic fixtures (`RecallEdgeCaseTests`).
- [x] Cycle cannot hang or loop (`test_cycle_terminates...` also asserts no false truncation).
- [x] Output equals the generator's independent ground truth: 0 false positives / 0 false negatives across CURRENT/ALL/AS_OF and 5 batches (`RecallGroundTruthTests`).
- [x] Missing links shown as warnings; "no gaps" text explicitly says it is not proof of completeness.
- [x] CSV (formula-injection escaped, `test_csv_formula_injection_escaped`) and JSON export with stable keys.

## Security and reliability
- [x] Server-side validation of every field (dates, lengths, enums, bodies; `test_input_validation`, `ApiSecurityTests`).
- [x] Parameterized SQL (identifier whitelists for the only dynamic column names); injection tests pass.
- [ ] **Authentication/authorization: NOT implemented.** Four demo roles with a permission matrix exist (`X-Demo-User`), clearly labelled "not authentication". Do not expose beyond localhost.
- [x] No secrets in repo. [x] No CORS headers; Host and Origin checks; JSON-only writes; CSP forbids inline script/style/eval (the browser test tripped it, proving it is active).
- [x] Errors never leak tracebacks/paths (`test_errors_never_leak_internals`).
- [x] Pagination (max 200) and bounded exports (5,000 rows).

## Visual and interaction quality
- [x] Light theme, flat surfaces, no gradients/shadows/emoji; status shown as small square + text, not pill badges.
- [x] KPI values are DB queries with definitions printed under each.
- [x] Inline field validation, no `alert()`; loading/empty/error/success/disabled states exist.
- [x] Checked at 1280, 1024 and 390 px: no console errors, no horizontal overflow on any of 12 pages (automated sweep + screenshots reviewed).
- [x] Tables use a deliberate small-screen pattern (stacked label/value rows at ≤640 px; scroll containers for dense tables).
- [ ] **Full keyboard-only walkthrough of every workflow: partially done.** Native `<dialog>` (focus trap, Esc closes) and `:focus-visible` outlines are in place and Esc/Tab behaviour was exercised; a complete screen-reader pass was NOT done.

## Research and performance
- [ ] **Same dataset in PostgreSQL and Neo4j: NOT done.** Only relational strategies inside SQLite were compared. No graph database was run.
- [x] Each benchmark asserts correctness vs ground truth before timing (`test_tiny_scale_all_strategies_correct`).
- [x] Settings, versions, seed, hardware, indexes, repetitions recorded in `research/benchmark_results.json`.
- [x] p50/p95 from raw repeated samples; regenerate with `python benchmarks/run_benchmark.py`.
- [x] Claims separate measured / hypothesis / not-measured; no universal-winner claim; one unexpected result reported as found (BFS beat the recursive CTE on whole-batch recall).

## Documentation
- [x] README, architecture decisions, ERD + live schema page, API list, state machine, viva guide (`docs/VIVA_GUIDE.md`), experiment write-up (`docs/EXPERIMENT.md`).
- [x] Synthetic data and non-compliance disclosed in UI banner, footer and README.
