# Architecture decisions

## 1. Why SQLite for the teaching build?

The course project needs to be runnable on a student laptop without cloud services or dependency installation. SQLite gives a real relational database, constraints, transactions, and indexes in one local file. This is a prototype choice, not a claim that SQLite is the right production database for a multi-organization passport network.

## 2. Why are events stored separately from the current asset status?

The current status is useful for fast filtering. The event table preserves the recorded history of what happened and when. In a production design, current state should be reconciled against event history, and event corrections should be audited rather than silently rewriting the past.

## 3. Why are component relationships dated?

A module can be removed from one pack and installed in another. `valid_from` and `valid_to` represent when a relationship is considered active in this demo. The prototype's integrity checks flag multiple open parents but do not yet implement a full, evidence-backed transfer workflow.

## 4. Why are passport versions separate rows?

A lifecycle transition may require a new passport version that points to the previous version. The partial unique index allows at most one ACTIVE passport per asset, while `UNIQUE(asset_id, passport_version)` prevents duplicate version numbers for that asset.

## 5. Why no blockchain in the core prototype?

A blockchain does not validate whether a person entered truthful source data. It can make some later changes detectable under specific trust assumptions, but it adds governance and operational complexity. The first research question should be whether the relational model and controlled event workflow meet the defined integrity needs.

## 6. Known limits

- Synthetic seed records; no real manufacturer or vehicle data.
- No user authentication or organization-level permissions.
- No signed evidence, sensor ingestion, QR passport resolver or legal compliance certification.
- SQLite local deployment, not a multi-region distributed service.
- Integrity checks are a small explicit rule set, not a full regulatory rules engine.
- Graph traversal is computed from relational rows; there is no Neo4j implementation yet.
- The prototype does not make measured performance claims. Run controlled experiments before reporting performance.

## 7. v2 decisions
- **Triggers after seed** so legacy defects remain findable; update-overlap trigger fires only on *newly introduced* overlap so repairs are possible.
- **Hierarchy as data (HierarchyRule)** rather than hard-coded: removes a transitive dependency and makes the graph acyclic by construction.
- **Idempotency key over natural-key dedupe**: identical events can legitimately repeat (two inspections on one day), so request identity is explicit.
- **Hash chain, not blockchain**: detects some edits cheaply; limits are tested rather than hidden.
- **Recursive CTE kept despite the benchmark**: it is the readable, single-statement, teachable form and supports AS_OF/ALL; the measured path re-walking cost is documented with a proposed fix.
- **Read-only SQL lab with five layers** (ro connection, query_only, authorizer, single statement/prefix check, row+time caps); local teaching use only.
