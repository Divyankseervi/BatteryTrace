# Codex Instructions — BatteryTrace

## Product mission
Turn BatteryTrace into a credible, final-year-level engineering project: an evidence-aware EV battery passport and lifecycle traceability system with strong relational modeling, component lineage, integrity controls, reproducible experiments, and a carefully designed light dashboard. It must remain understandable to a B.Tech CSE student and defensible in a viva.

## Read these before editing
1. `README.md` — current behaviour and run instructions.
2. `docs/ARCHITECTURE_DECISIONS.md` — why the current design is intentionally small.
3. `docs/RESEARCH_REVIEW.md` — prior art and claims that must not be repeated as novelty.
4. `docs/NEXT_LEVEL_ROADMAP.md` — staged target architecture and priorities.
5. `docs/ACCEPTANCE_CHECKLIST.md` — definition of done.
6. `tests/test_smoke.py` — the existing baseline regression suite.

## Current baseline — do not assume more than this
- A small Python standard-library HTTP server (`server.py`).
- Static light-theme frontend (`index.html`).
- SQLite database with `Asset`, `Passport`, `AssetRelationship`, and `LifecycleEvent` data.
- Seed records are synthetic; two integrity issues are deliberately seeded for demonstration.
- Six existing smoke tests pass as of the handoff build. Re-run them yourself before changing code.
- Lineage traversal is performed over relational rows. There is no real Neo4j backend yet.
- No real manufacturer integration, authentication, legal-compliance certification, live telemetry, or published benchmark results.

## Working rules
- First run the baseline tests and inspect the code. Then state a short implementation plan in your work log and execute it; do not stop after writing a plan.
- Make incremental changes and run tests after every meaningful batch. Preserve a working app at all times.
- Keep a `CHANGELOG.md` entry for user-visible or architecture changes.
- Add dependencies only when they provide real value. Pin them. Provide a simple Windows setup path and a repeatable clean install.
- Never fabricate test output, benchmark results, real-world events, compliance status, user identities, battery metrics, or citations.
- Clearly label all generated/demo data as synthetic. Do not label deterministic test findings as proof of physical truth, fraud, or legal non-compliance.
- Do not claim a feature is complete unless there is code and a test or a clearly documented manual verification procedure.
- Avoid a huge, risky rewrite in one pass. If a modern-stack migration is justified, make the migration in a dedicated phase with a baseline-compatible run path and documented rollback.
- Keep business rules out of frontend-only JavaScript. Validate inputs in the backend and enforce critical invariants at the data layer where feasible.
- Do not add blockchain, AI/LLM features, vector databases, microservices, or Kubernetes merely to make the project sound advanced. Each addition needs a specific use case and measurable acceptance criterion.

## Visual design constraints
Create a human-designed industrial / enterprise operations dashboard, not a generic AI-generated SaaS template.
- Light theme only by default: white and warm-white surfaces, black/charcoal text, fine neutral borders, restrained muted-green or amber status accents.
- No dark mode, gradients, glowing elements, glassmorphism, giant marketing hero, oversized KPI cards, excessive pill badges, or ornamental empty charts.
- Use a clear hierarchy, compact page title + one-sentence purpose, left navigation, dense but readable tables, aligned numbers, consistent 8px spacing scale, subtle borders, restrained 4–8px radii, and useful filter/action placement.
- Prefer real operational details over decorative visuals: last event, passport status, lineage depth, missing evidence, and next action.
- Implement loading, empty, error, validation, confirmation, and success states. Avoid `alert()` for normal workflows.
- Responsive layout must work at 1280px desktop, 1024px tablet, and 390px mobile. Keyboard focus and accessible labels are required.
- Charts only when they answer a defined operational question. Always label units and data provenance.
- Make design choices consistent across pages; don't invent a new visual language per screen.

## Engineering standard
- Domain model and schema constraints are documented.
- Lifecycle transitions are explicit and validated.
- Passport version links are valid and cannot form accidental cycles.
- Component relationships have a defined temporal model. A component must not have two incompatible active parent assignments unless the domain explicitly allows it.
- Retried requests must not accidentally create duplicate lifecycle events where idempotency is required.
- Rejected operations do not partially mutate data.
- Event changes and state changes use atomic transactions.
- Every database migration is reversible or has a documented forward-recovery plan.
- Security basics: no hardcoded secrets, bind SQL parameters, validate input, use least privilege, avoid permissive production CORS, and do not expose internal tracebacks to clients.
- Exported data must be bounded, scoped, and escaped correctly for CSV spreadsheet use.
- Benchmark comparisons must use the same generated source dataset, identical query definitions, disclosed hardware/software, warm-up runs, repeated measurements, and correctness checks. Report p50/p95 and errors; do not benchmark only one run.

## Definition of done for each feature
1. The behaviour is documented in plain language.
2. Positive, negative, and edge cases are tested.
3. Existing tests still pass.
4. Setup instructions are current and work from a clean checkout.
5. The frontend is checked at desktop and mobile widths or the limitation is stated.
6. Any performance claim is backed by repeatable output committed under `research/` or `benchmarks/`.
7. The final response lists what changed, exact tests run, results, and known limitations.

## How to work
Use `docs/NEXT_LEVEL_ROADMAP.md` as the project backlog. Prefer finishing a small vertical slice end-to-end over scaffolding many half-finished features. Do not ask for confirmation for routine implementation choices. If time or context is limited, ship the highest-value complete phase and record the remaining work explicitly.

## Research and reuse discipline
- Existing projects and papers in `docs/RESEARCH_REVIEW.md` are prior art, not a permission to copy code without checking each repository's license.
- Before adding third-party code or a dependency, record its source, license, version, and why it is needed. Attribute reused ideas and follow license terms.
- Re-verify paper metadata, repository status, standards and regulation wording before using them in a formal submission. Do not treat a search snippet as a complete citation.
