"""Optional Neo4j graph projection backed by the authoritative SQLite database.

Neo4j is deliberately not required to start BatteryTrace. Set NEO4J_PASSWORD
to enable the HTTP client, then use the graph sync endpoint to project the
current SQLite assets and relationships.
"""
from __future__ import annotations

import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


URI = os.environ.get('NEO4J_URI', 'http://127.0.0.1:7474').rstrip('/')
USER = os.environ.get('NEO4J_USER', 'neo4j')
PASSWORD = os.environ.get('NEO4J_PASSWORD', '')
DATABASE = os.environ.get('NEO4J_DATABASE', 'neo4j')
TIMEOUT = 4


def configured() -> bool:
    return bool(PASSWORD)


def _tx_url() -> str:
    return f'{URI}/db/{DATABASE}/tx/commit'


def _request(url: str, payload: dict | None = None) -> dict:
    token = base64.b64encode(f'{USER}:{PASSWORD}'.encode('utf-8')).decode('ascii')
    headers = {'Accept': 'application/json', 'Authorization': f'Basic {token}'}
    data = None
    if payload is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(payload).encode('utf-8')
    request = Request(url, data=data, headers=headers, method='POST' if data else 'GET')
    with urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode('utf-8'))


def status() -> dict:
    if not configured():
        return {'configured': False, 'available': False, 'message': 'Set NEO4J_PASSWORD to enable Neo4j.'}
    try:
        _request(URI)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        # Do not return connection details or exception text through the public API.
        return {'configured': True, 'available': False, 'message': 'Neo4j is not reachable or rejected the configured credentials.'}
    return {'configured': True, 'available': True, 'uri': URI, 'database': DATABASE}


def _run(statements: list[dict]) -> list[dict]:
    result = _request(_tx_url(), {'statements': statements})
    errors = result.get('errors') or []
    if errors:
        raise RuntimeError(errors[0].get('message', 'Neo4j query failed.'))
    return result.get('results', [])


def sync(con) -> dict:
    if not configured():
        raise RuntimeError('Neo4j is not configured. Set NEO4J_PASSWORD first.')
    assets = [dict(row) for row in con.execute(
        'SELECT asset_code, asset_type, manufacturer, chemistry, capacity_kwh, batch_code, status, created_at FROM Asset'
    )]
    relationships = [dict(row) for row in con.execute(
        'SELECT r.relationship_id, p.asset_code AS parent_code, c.asset_code AS child_code, '
        'r.relationship_type, r.valid_from, r.valid_to '
        'FROM AssetRelationship r '
        'JOIN Asset p ON p.asset_id = r.parent_asset_id '
        'JOIN Asset c ON c.asset_id = r.child_asset_id'
    )]
    # Remove projected edges first so deleted or changed SQLite relationships do
    # not linger in the graph. IDs and values remain parameters, never Cypher text.
    _run([
        {'statement': 'MATCH ()-[r:RELATED]->() DELETE r', 'parameters': {}},
        {
            'statement': (
                'UNWIND $rows AS row '
                'MERGE (a:Asset {asset_code: row.asset_code}) '
                'SET a.asset_type = row.asset_type, a.manufacturer = row.manufacturer, '
                'a.chemistry = row.chemistry, a.capacity_kwh = row.capacity_kwh, '
                'a.batch_code = row.batch_code, a.status = row.status, a.created_at = row.created_at'
            ),
            'parameters': {'rows': assets},
        },
        {
            'statement': (
                'UNWIND $rows AS row '
                'MATCH (parent:Asset {asset_code: row.parent_code}), (child:Asset {asset_code: row.child_code}) '
                'MERGE (parent)-[r:RELATED {relationship_id: row.relationship_id}]->(child) '
                'SET r.relationship_type = row.relationship_type, r.valid_from = row.valid_from, r.valid_to = row.valid_to'
            ),
            'parameters': {'rows': relationships},
        },
    ])
    return {'synced_assets': len(assets), 'synced_relationships': len(relationships), 'database': DATABASE}


def lineage(asset_code: str, direction: str = 'down', max_depth: int = 8) -> dict:
    if not configured():
        raise RuntimeError('Neo4j is not configured. Set NEO4J_PASSWORD first.')
    if direction not in ('up', 'down'):
        raise ValueError('direction must be up or down')
    max_depth = max(1, min(int(max_depth), 20))
    arrow = '<-' if direction == 'up' else '-'
    reverse = '->' if direction == 'up' else '->'
    query = (
        f'MATCH p=(start:Asset {{asset_code: $asset_code}}){arrow}'
        f'[:RELATED*1..{max_depth}]{reverse}(node:Asset) '
        'RETURN [n IN nodes(p) | n.asset_code] AS path, '
        '[n IN nodes(p) | n.asset_type] AS types '
        'ORDER BY length(p), path'
    )
    results = _run([{'statement': query, 'parameters': {'asset_code': asset_code}}])
    rows = results[0].get('data', {}).get('rows', []) if results else []
    return {'asset_code': asset_code, 'direction': direction, 'paths': [
        {'path': row[0], 'types': row[1], 'depth': len(row[0]) - 1} for row in rows
    ]}
