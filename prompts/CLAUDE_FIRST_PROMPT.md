# Paste this into Claude Code after opening this folder

You are the lead engineer for BatteryTrace. Read `CLAUDE.md`, `HANDOFF_TO_CLAUDE.md`, `docs/NEXT_LEVEL_ROADMAP.md`, `docs/ACCEPTANCE_CHECKLIST.md`, current README, architecture decisions, research review, and all current routes/templates/tests before making edits.

**Do not give me only a plan.** First run the existing test suite, inspect the current implementation, and write a factual current-state audit to `docs/CURRENT_STATE_AUDIT.md`. Then start Sprint 1 from `docs/CLAUDE_WORK_PLAN.md` in the same working session: add meaningful tests around lifecycle state transitions, component transfer, passport version chains, transaction rollback and duplicate submissions; fix correctness bugs found; run the complete test suite; update docs and CHANGELOG. Keep the baseline working and do not fabricate test outcomes.

The final goal is a final-year-level project with a genuinely professional, light, human-designed engineering operations dashboard. The meaningful differentiators should be lifecycle integrity, temporal component lineage, targeted recall completeness, evidence-aware audit history, and a reproducible relational-versus-graph database experiment. Avoid generic AI-generated SaaS styling, decorative charts, gradients, dark mode, fake live data, and unimplemented “AI” claims. Do not claim regulatory compliance. Explicitly label all records as synthetic.

Use the roadmap in order, prioritizing correctness and tested workflows before framework migration or feature count. If you choose FastAPI/SQLAlchemy/PostgreSQL/Neo4j or a modern frontend, document why, pin dependencies, add migrations and tests, and preserve a no-surprises Windows setup guide. Benchmark only after output correctness has been asserted, and save raw samples and environment metadata.

At the end, report exact commands executed, test counts/results, files changed, features actually verified, visual checks completed, and remaining limitations. Do not tell me something was tested unless you ran the test.
