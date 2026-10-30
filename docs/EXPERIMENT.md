# Experiment: relational traversal strategies (SQLite)

**Question.** For "which packs/vehicles contain these cells?", how do three relational strategies compare, and what do indexes change?
**Not the question.** PostgreSQL vs Neo4j. No graph database was run, so no such claim is made anywhere in this project.

## Method
`tools/synthetic.py` builds a deterministic fleet (seed 42): vehicles → packs → modules → cells, production batches, module churn between packs, and second-life moves to storage systems. The generator keeps its own interval lists, so the *expected* answer is known by construction and is computed by a deliberately different algorithm (fix-point scan) than the SQL.
Strategies: `recursive_cte` (the app's), `app_bfs_n_plus_1` (one indexed query per visited asset), `closure_table` (precomputed ancestors), `recursive_cte_noidx` (indexes dropped). Each answer is compared to ground truth before its time counts. 5 warm-up runs, 30 timed samples, `perf_counter_ns`, p50 and p95.
Reproduce: `python benchmarks/run_benchmark.py` (about 3–4 minutes; writes `research/benchmark_results.json`, shown on DBMS lab → Experiment).

## Results from the committed run (1-CPU sandbox VM, in-memory DB, SQLite 3.45)
| Scale | Whole-batch ancestors: CTE | BFS | Closure | One cell, indexed (CTE) | One cell, no index (CTE) |
|---|---|---|---|---|---|
| 1.5k assets | 3.2 ms | 1.1 ms | 0.56 ms | 0.017 ms | 0.63 ms |
| 15k assets | 48.6 ms | 11.7 ms | 6.9 ms | 0.022 ms | 6.3 ms |
| 90k assets | 580 ms | 78 ms | 52 ms | 0.018 ms | 41 ms |
Closure build: 10 ms / 127 ms / 630 ms.
**Variance warning:** two runs of the same script on the same machine differed by up to ~50% on small timings (1.5k-asset CTE: 4.8 ms in the first run, 3.2 ms in the committed one). Ratios between strategies were stable; absolute milliseconds are not.

## What the data supports
1. All strategies returned exactly the ground-truth set at every scale.
2. **Indexes dominate** point lookups: roughly 2,000× at 90k assets (0.018 ms vs 41 ms), and the plan changes from SEARCH … USING INDEX to SCAN (recorded in the JSON).
3. **Surprise:** the plain-Python BFS beat the recursive CTE on whole-batch recall by about 7× at 90k assets (580 ms vs 78 ms). Likely cause (a hypothesis consistent with the numbers, not separately profiled): the CTE enumerates every *path*, so an ancestor shared by many cells is re-walked per path, while BFS visits each asset once.
4. The closure table is fastest but is a snapshot of current links, costs a rebuild on every transfer/recycle, and cannot answer as-of-date questions without storing history.

## Threats to validity / not measured
Single machine and run; in-memory DB (no disk I/O); in-process BFS (no network round trips, which would hurt BFS); one synthetic shape (strict tree plus churn, no wide fan-in); temporal AS_OF/ALL modes and concurrent readers not timed; no PostgreSQL or Neo4j.

## Next steps if you extend this
Implement the distinct-asset CTE (`UNION`, no path column) and re-measure; run the same generator into PostgreSQL (`WITH RECURSIVE`) and Neo4j (Cypher variable-length paths) with identical correctness checks; only then discuss a relational-vs-graph conclusion.
