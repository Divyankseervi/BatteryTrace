"""Deterministic synthetic fleet generator WITH ground truth.

Same seed -> identical dataset. The expected recall sets are derived from the generator's own
bookkeeping (plain Python lists of intervals), NOT from the SQL traversal under test, so a
test can compare "what the database returned" with "what we know is true by construction".
All data is synthetic.
"""
from __future__ import annotations
import random, datetime

BASE = datetime.date(2023, 1, 1)


def _d(n):
    return (BASE + datetime.timedelta(days=n)).isoformat()


class GroundTruth:
    def __init__(self):
        self.code = {}          # asset_id -> code
        self.batch_cells = {}   # batch -> [cell asset_id]
        self.links = []         # (parent_id, child_id, from, to)  to=None means open
        self.today = _d(1500)

    def _parents(self, child, mode, as_of):
        out = []
        for p, c, f, t in self.links:
            if c != child:
                continue
            if mode == 'ALL' or (mode == 'CURRENT' and t is None) or (mode == 'AS_OF' and f <= as_of and (t is None or t > as_of)):
                out.append(p)
        return out

    def expected_up(self, start_ids, mode='CURRENT', as_of=None):
        """Naive fix-point ancestor search, written differently from the SQL CTE on purpose."""
        found = set(start_ids)
        grew = True
        while grew:
            grew = False
            for a in list(found):
                for p in self._parents(a, mode, as_of):
                    if p not in found:
                        found.add(p); grew = True
        return {self.code[i] for i in found}

    def expected_batch(self, batch, mode='CURRENT', as_of=None):
        return self.expected_up(self.batch_cells[batch], mode, as_of)

    def expected_down(self, start_id, mode='CURRENT', as_of=None):
        found, grew = {start_id}, True
        while grew:
            grew = False
            for p, c, f, t in self.links:
                if p in found and c not in found:
                    ok = mode == 'ALL' or (mode == 'CURRENT' and t is None) or (mode == 'AS_OF' and f <= as_of and (t is None or t > as_of))
                    if ok:
                        found.add(c); grew = True
        return {self.code[i] for i in found}


def generate(con, seed=42, vehicles=20, modules_per_pack=4, cells_per_module=6, batches=5,
             churn_rate=0.15, second_life_rate=0.15):
    """Insert a synthetic fleet into `con` (schema must exist; triggers optional) and return GroundTruth."""
    rng = random.Random(seed)
    gt = GroundTruth()
    assets, links = [], []
    n = 0

    def new(code, typ, status='ACTIVE', batch=None, created=0, chem='NMC'):
        nonlocal n
        n += 1
        aid = f'G{n:08d}'
        gt.code[aid] = code
        assets.append((aid, code, typ, 'Synthetic Works', chem, None, batch, status, _d(created)))
        return aid

    batch_names = [f'SYN-B{b:02d}' for b in range(batches)]
    for b in batch_names:
        gt.batch_cells[b] = []
    packs, modules_of = [], {}
    stores = [new(f'STORE-{i:04d}', 'STORAGE_SYSTEM', created=5) for i in range(max(1, vehicles // 8))]
    for v in range(vehicles):
        veh = new(f'VEH-{v:04d}', 'VEHICLE', created=10)
        pack = new(f'PACK-{v:04d}', 'BATTERY_PACK', created=10)
        packs.append(pack)
        if rng.random() < second_life_rate:        # pack leaves the vehicle for a storage system
            moved = 400 + rng.randint(0, 100)
            st = rng.choice(stores)
            links += [(veh, pack, 'INSTALLED_IN', _d(20), _d(moved)), (st, pack, 'USES', _d(moved), None)]
        else:
            links.append((veh, pack, 'INSTALLED_IN', _d(20), None))
        modules_of[pack] = []
        for m in range(modules_per_pack):
            mod = new(f'MOD-{v:04d}-{m}', 'MODULE', created=11, batch=f'SYN-M{rng.randint(0, 2)}')
            modules_of[pack].append(mod)
            links.append((pack, mod, 'CONTAINS', _d(30), None))
            for c in range(cells_per_module):
                b = rng.choice(batch_names)
                cell = new(f'CELL-{v:04d}-{m}-{c}', 'CELL', batch=b, created=12)
                gt.batch_cells[b].append(cell)
                links.append((mod, cell, 'CONTAINS', _d(31), None))
    # churn: some modules move to another pack (old link closed, new link opened at the same date)
    mods = [(p, m) for p, ms in modules_of.items() for m in ms]
    for i, (p, m) in enumerate(mods):
        if rng.random() < churn_rate and len(packs) > 1:
            target = rng.choice([q for q in packs if q != p])
            day = 600 + i % 300
            for k, (par, ch, typ, f, t) in enumerate(links):
                if ch == m and t is None and par == p:
                    links[k] = (par, ch, typ, f, _d(day))
            links.append((target, m, 'CONTAINS', _d(day), None))
    con.executemany('INSERT INTO Asset VALUES (?,?,?,?,?,?,?,?,?)', assets)
    con.executemany('INSERT INTO AssetRelationship(parent_asset_id,child_asset_id,relationship_type,valid_from,valid_to) VALUES (?,?,?,?,?)',
                    [(p, c, t, f, to) for p, c, t, f, to in links])
    gt.links = [(p, c, f, to) for p, c, t, f, to in links]
    gt.counts = {'assets': len(assets), 'links': len(links)}
    return gt
