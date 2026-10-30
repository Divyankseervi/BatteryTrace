# Handoff brief: take BatteryTrace to a final-year project

You are extending an existing student engineering project. The accompanying plain-language case study is included in `reference/EV_Battery_Passport_DBMS_Case_Study_Black_Font.docx`. Do not replace the working base with a generic starter template. Read `CLAUDE.md` and `docs/NEXT_LEVEL_ROADMAP.md`, inspect the current application and tests, and keep the original working baseline understandable.

## Project identity
**BatteryTrace — Evidence-Aware EV Battery Passport & Circular Lifecycle Intelligence**

The system models cells, modules, battery packs, vehicles/storage systems, passports, dated parent-child relationships and lifecycle events. The key research question is how database architecture and integrity rules affect lineage correctness, recall completeness and trace-query performance across battery reuse, repair, remanufacturing and recycling.

## Engineering differentiators we want
1. **A trustworthy lifecycle domain model** — explicit state machine, temporal component membership, passport version chain, validation rules and atomic transitions.
2. **Evidence-aware auditability** — append-only audit events and a tamper-evident hash chain, with explicit caveats that hashes detect some changes but do not prove that source data was truthful.
3. **Component genealogy and recall simulation** — trace all descendants/parents of a batch or cell and export the affected packs/assets, with completeness tests against known ground truth.
4. **A real, reproducible database comparison** — relational baseline plus optional graph database implementation; identical generated records and query scenarios; correctness before speed; p50/p95 latency and benchmark metadata.
5. **Role-aware operations** — manufacturer, service organization, recycler, and auditor roles, seeded test users only, least-privilege permissions and a clear demo mode.
6. **A polished light operations interface** — quiet visual hierarchy, practical data density, credible tables, timeline, filters and meaningful states. No generic AI-template aesthetics.
7. **A strong teaching/viva layer** — architecture diagram, ERD, schema notes, query plan examples, experiment methodology, limitations, and explainers mapped to the DBMS syllabus.

## Non-goals
- Do not claim this is EU-regulation compliant or an official passport system.
- Do not invent real battery data or present the fictional organizations as real.
- Do not claim graph databases always outperform relational databases.
- Do not add blockchain or AI just for marketing. If a model is ever added, it must use explicit data, evaluation, and a narrow purpose.
- Do not hide limitations or make the dashboard imply that rule-based warnings prove fraud or actual battery safety.

## First execution sequence
1. Run `python -m unittest discover -s tests -v` in the project root and save the result in your notes.
2. Review all API routes, database operations, frontend navigation and known limitations.
3. Create a prioritized issue list based on correctness/security first, research validity second, UI polish third.
4. Implement in small phases. Keep the baseline runnable after each phase.
5. Add/update tests and docs before declaring a feature finished.
6. Finish with a clean install/test run and report known gaps honestly.

## Deliverables expected from your work
- Runnable code and pinned dependencies where needed.
- `README.md` that works on Windows and Linux.
- Updated `CLAUDE.md`, `CHANGELOG.md`, architecture decision records and schema docs.
- Tests for normal, invalid, boundary, concurrent and recovery cases where applicable.
- A reproducible benchmark tool with generated fixtures and raw results (only if the benchmark phase is actually run).
- A clearly scoped demonstration script and concise viva guide.

## Research hygiene
Treat `docs/RESEARCH_REVIEW.md` as the starting bibliography. Verify the exact paper metadata, standard version, repository activity and license before incorporating claims or code. Do not plagiarize implementation from GitHub; follow licenses and attribute external work. Distinguish a design hypothesis, a test result and a published finding.
