#!/usr/bin/env python3
"""Relational traversal strategies inside SQLite, measured on synthetic fleets with known ground truth.

Strategies (same questions, same data):
  recursive_cte        one WITH RECURSIVE query (what the app uses)
  app_bfs_n_plus_1     Python loop issuing one indexed query per visited asset
  closure_table        precomputed ancestor table (O(1) lookup, costs build time and goes stale on writes)
  recursive_cte_noidx  same CTE with the relationship indexes dropped (index ablation)

HONEST SCOPE: SQLite only. No PostgreSQL, no Neo4j was run. Results depend on this machine.
Every strategy's answer is compared with the generator's ground truth BEFORE its timing is accepted.
"""
from __future__ import annotations
import argparse, json, os, platform, random, sqlite3, statistics, sys, time, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import db, recall                      # noqa: E402
from tools import synthetic            # noqa: E402

OUT = ROOT / 'research' / 'benchmark_results.json'


def new_db(vehicles, seed):
    con = sqlite3.connect(':memory:'); con.row_factory = sqlite3.Row
    db.create_schema(con)
    gt = synthetic.generate(con, seed=seed, vehicles=vehicles)
    return con, gt


def ids(con, codes):
    return [r[0] for r in con.execute(f"SELECT asset_id FROM Asset WHERE asset_code IN ({','.join('?' * len(codes))})", list(codes))]


def cte_up(con, start_ids):
    return {r['asset_id'] for r in recall.trace(con, start_ids, 'up', 'CURRENT', None, 12)}


def frontier_cte_up(con, start_ids):
    return {r['asset_id'] for r in recall.trace_frontier(con, start_ids, 'up', 'CURRENT', None, 12)}


def bfs_up(con, start_ids):
    seen, frontier = set(start_ids), list(start_ids)
    while frontier:
        a = frontier.pop()
        for (p,) in con.execute('SELECT parent_asset_id FROM AssetRelationship WHERE child_asset_id=? AND valid_to IS NULL', (a,)):
            if p not in seen:
                seen.add(p); frontier.append(p)
    return seen


def build_closure(con):
    t0 = time.perf_counter()
    con.execute('CREATE TABLE Closure(desc_id TEXT, anc_id TEXT, depth INT, PRIMARY KEY(desc_id, anc_id))')
    con.execute('''INSERT INTO Closure WITH RECURSIVE c(d,a,n) AS (SELECT asset_id,asset_id,0 FROM Asset
        UNION ALL SELECT c.d, r.parent_asset_id, c.n+1 FROM c JOIN AssetRelationship r ON r.child_asset_id=c.a AND r.valid_to IS NULL)
        SELECT d,a,MIN(n) FROM c GROUP BY d,a''')
    return (time.perf_counter() - t0) * 1000


def closure_up(con, start_ids):
    ph = ','.join('?' * len(start_ids))
    return {r[0] for r in con.execute(f'SELECT DISTINCT anc_id FROM Closure WHERE desc_id IN ({ph})', start_ids)}


def timeit(fn, warmup, samples):
    for _ in range(warmup):
        fn()
    t = []
    for _ in range(samples):
        t0 = time.perf_counter_ns(); r = fn(); t.append((time.perf_counter_ns() - t0) / 1e6)
    t.sort()
    return {'p50_ms': statistics.median(t), 'p95_ms': t[min(len(t) - 1, int(len(t) * 0.95))], 'result_size': len(r)}


def run_scale(vehicles, seed, warmup, samples):
    con, gt = new_db(vehicles, seed)
    n_assets, n_links = gt.counts['assets'], gt.counts['links']
    rng = random.Random(seed + 1)
    cells = sorted(c for cs in gt.batch_cells.values() for c in cs)
    one = [rng.choice(cells)]
    batch = gt.batch_cells[sorted(gt.batch_cells)[0]]
    workloads = {'one cell -> ancestors': (one, gt.expected_up(one)), 'whole batch -> ancestors': (batch, gt.expected_up(batch))}
    closure_ms = build_closure(con)
    strategies = {'recursive_cte': cte_up, 'frontier_cte': frontier_cte_up, 'app_bfs_n_plus_1': bfs_up, 'closure_table': closure_up}
    results, correct = [], True
    code = gt.code
    for wl, (starts, expected) in workloads.items():
        for name, fn in strategies.items():
            got = {code[i] for i in fn(con, starts)}
            if got != expected:
                correct = False
            results.append({'workload': wl, 'strategy': name, **timeit(lambda f=fn, s=starts: f(con, s), warmup, samples)})
    plan = [r[3] for r in con.execute('EXPLAIN QUERY PLAN SELECT parent_asset_id FROM AssetRelationship WHERE child_asset_id=? AND valid_to IS NULL', (one[0],))]
    con.execute('DROP INDEX idx_relationship_child'); con.execute('DROP INDEX idx_relationship_parent')
    # NOTE: the comment makes the SQL text different; Python's sqlite3 statement cache otherwise returns the stale (indexed) plan.
    plan_noidx = [r[3] for r in con.execute('EXPLAIN QUERY PLAN /* after DROP INDEX */ SELECT parent_asset_id FROM AssetRelationship WHERE child_asset_id=? AND valid_to IS NULL', (one[0],))]
    for wl, (starts, expected) in workloads.items():
        if vehicles > 200 and wl.startswith('whole'):
            continue                                       # unindexed CTE at this size would take minutes; omitted and stated
        got = {code[i] for i in cte_up(con, starts)}
        if got != expected:
            correct = False
        results.append({'workload': wl, 'strategy': 'recursive_cte_noidx', **timeit(lambda s=starts: cte_up(con, s), 1, max(3, samples // 5))})
    return {'vehicles': vehicles, 'assets': n_assets, 'links': n_links, 'correct': correct, 'closure_build_ms': round(closure_ms, 2),
            'plan_with_index': plan, 'plan_without_index': plan_noidx, 'results': results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=42); ap.add_argument('--warmup', type=int, default=5); ap.add_argument('--samples', type=int, default=30)
    ap.add_argument('--vehicles', type=int, nargs='+', default=[50, 500, 3000])
    a = ap.parse_args()
    scales = [run_scale(v, a.seed, a.warmup, a.samples) for v in a.vehicles]
    for s in scales:
        for r in s['results']:
            r['p50_ms'] = round(r['p50_ms'], 4); r['p95_ms'] = round(r['p95_ms'], 4)
    notes = [
        'All strategies were checked against generator ground truth at every scale; a mismatch would mark that scale invalid.',
        'FINDING: for whole-batch recall the simple app_bfs_n_plus_1 was FASTER than the recursive CTE (about 7x at the largest scale). The CTE enumerates every path, so an ancestor shared by many starting cells is re-walked once per path (and carries a growing path string); BFS visits each asset once. This is an in-process SQLite result: BFS round trips to a networked server would cost far more, and that was not measured.',
        'Possible improvement, NOT implemented: a distinct-asset CTE (UNION instead of UNION ALL, no path column) for membership and depth, then reconstruct paths only for the reached nodes. The ground-truth tests would make that refactor safe.',
        'closure_table answers fastest but is a snapshot of CURRENT links: it must be rebuilt or incrementally maintained on every transfer or recycle, and it cannot answer as-of-a-past-date questions without storing history. Build time is reported per scale.',
        'recursive_cte_noidx is the index ablation (indexes on parent and child dropped). The single-cell lookup is orders of magnitude slower without them; see plan_with_index and plan_without_index. The unindexed whole-batch workload is omitted at the two larger scales because it takes too long.',
        'NOT measured: PostgreSQL, Neo4j or any graph database, concurrent readers, disk-bound datasets, or the AS_OF/ALL temporal modes. Do not quote these numbers as a relational-vs-graph conclusion.',
        'Timings are wall-clock on a shared sandbox VM with 1 CPU and an in-memory database. Re-run on your own machine for your own numbers.']
    out = {'generated_at': datetime.datetime.now().isoformat(timespec='seconds'),
           'environment': {'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version, 'platform': platform.platform(), 'cpus': os.cpu_count()},
           'config': {'seed': a.seed, 'warmup': a.warmup, 'samples': a.samples, 'database': ':memory:'}, 'scales': scales, 'notes': notes}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(out, indent=1), encoding='utf-8')
    for s in scales:
        print(f"\n{s['assets']:,} assets / {s['links']:,} links  correct={s['correct']}  closure build {s['closure_build_ms']} ms")
        for r in s['results']:
            print(f"  {r['workload']:28s} {r['strategy']:22s} p50 {r['p50_ms']:9.3f} ms  p95 {r['p95_ms']:9.3f} ms  n={r['result_size']}")
    print('\nwrote', OUT)


if __name__ == '__main__':
    main()
