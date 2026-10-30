"""Domain rules for BatteryTrace: the lifecycle state machine, roles and validation.

Pure Python, no database access. This is the one place that answers
"is this event allowed for an asset in this state, by this role?".
The database triggers (sql/triggers.sql) are a second, independent safety net.
"""
from __future__ import annotations
import datetime, re

ASSET_TYPES = ('CELL', 'MODULE', 'BATTERY_PACK', 'VEHICLE', 'STORAGE_SYSTEM')
ASSET_STATUSES = ('ACTIVE', 'IN_REPAIR', 'SECOND_LIFE', 'RECYCLED', 'RETIRED')
TERMINAL_STATUSES = ('RECYCLED', 'RETIRED')
EVIDENCE_STATUSES = ('UNKNOWN', 'SELF_REPORTED', 'VERIFIED')
ROLES = ('MANUFACTURER', 'SERVICE', 'RECYCLER', 'AUDITOR')

# parent_type, child_type, relationship label. Mirrors the HierarchyRule table.
HIERARCHY = (
    ('BATTERY_PACK', 'MODULE', 'CONTAINS'),
    ('MODULE', 'CELL', 'CONTAINS'),
    ('VEHICLE', 'BATTERY_PACK', 'INSTALLED_IN'),
    ('STORAGE_SYSTEM', 'BATTERY_PACK', 'USES'),
)

ALL_LIVE = {'ACTIVE', 'IN_REPAIR', 'SECOND_LIFE'}

# event_type -> rule.  `from` = statuses in which the event is legal.
# `to` = new asset status (None = unchanged; 'RETURN' = see return_status()).
TRANSITIONS = {
    'MANUFACTURED':   {'from': {'ACTIVE'},                 'to': None,          'once': True},
    'ASSEMBLED':      {'from': {'ACTIVE', 'SECOND_LIFE'},  'to': None},
    'INSTALLED':      {'from': {'ACTIVE', 'SECOND_LIFE'},  'to': None},
    'TESTED':         {'from': ALL_LIVE,                   'to': None},
    'INSPECTED':      {'from': ALL_LIVE,                   'to': None},
    'TRANSFERRED':    {'from': ALL_LIVE,                   'to': None},
    'REPAIR_STARTED': {'from': {'ACTIVE', 'SECOND_LIFE'},  'to': 'IN_REPAIR'},
    'REPAIRED':       {'from': {'IN_REPAIR'},              'to': 'RETURN'},
    'REPURPOSED':     {'from': {'ACTIVE'},                 'to': 'SECOND_LIFE', 'types': {'BATTERY_PACK'}, 'needs_active_passport': True},
    'RECYCLED':       {'from': ALL_LIVE,                   'to': 'RECYCLED'},
}
EVENT_TYPES = tuple(TRANSITIONS)

# Demo roles (NOT authentication; see README). Which event types each role may record.
ROLE_EVENTS = {
    'MANUFACTURER': {'MANUFACTURED', 'ASSEMBLED', 'INSTALLED', 'TESTED', 'INSPECTED', 'TRANSFERRED'},
    'SERVICE':      {'ASSEMBLED', 'INSTALLED', 'TESTED', 'INSPECTED', 'TRANSFERRED', 'REPAIR_STARTED', 'REPAIRED', 'REPURPOSED'},
    'RECYCLER':     {'INSPECTED', 'TESTED', 'TRANSFERRED', 'RECYCLED'},
    'AUDITOR':      set(),
}
ROLE_CAN_RELINK = {'MANUFACTURER': True, 'SERVICE': True, 'RECYCLER': False, 'AUDITOR': False}

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class DomainError(Exception):
    """A rule was violated. `status` is the HTTP status the API should answer with."""
    def __init__(self, message: str, code: str = 'RULE_VIOLATION', status: int = 400):
        super().__init__(message)
        self.code, self.status = code, status


def parse_date(value, field='date') -> str:
    s = str(value or '').strip()
    if not DATE_RE.match(s):
        raise DomainError(f'{field} must use YYYY-MM-DD format.', 'BAD_DATE')
    try:
        datetime.date.fromisoformat(s)
    except ValueError:
        raise DomainError(f'{field} is not a real calendar date.', 'BAD_DATE')
    return s


def today() -> str:
    return datetime.date.today().isoformat()


def return_status(has_repurposed_event: bool) -> str:
    """After a repair a second-life pack stays second-life; everything else becomes ACTIVE."""
    return 'SECOND_LIFE' if has_repurposed_event else 'ACTIVE'


def check_transition(event_type, asset_type, status, role, *, already_manufactured=False, has_active_passport=True):
    """Return the rule dict if allowed, else raise DomainError. Never touches the database."""
    rule = TRANSITIONS.get(event_type)
    if rule is None:
        raise DomainError(f'Unknown event type: {event_type}', 'BAD_EVENT_TYPE')
    if event_type not in ROLE_EVENTS.get(role, set()):
        raise DomainError(f'Role {role} is not permitted to record {event_type} events.', 'FORBIDDEN', 403)
    if status in TERMINAL_STATUSES:
        raise DomainError(f'Asset is {status} (terminal): no further lifecycle events can be recorded.', 'TERMINAL_STATE', 409)
    if rule.get('types') and asset_type not in rule['types']:
        raise DomainError(f'{event_type} is only supported for {", ".join(sorted(rule["types"]))} assets.', 'WRONG_ASSET_TYPE', 409)
    if status not in rule['from']:
        raise DomainError(f'{event_type} is not allowed while the asset is {status}. Allowed from: {", ".join(sorted(rule["from"]))}.', 'ILLEGAL_TRANSITION', 409)
    if rule.get('once') and already_manufactured:
        raise DomainError('MANUFACTURED can only be recorded once per asset.', 'DUPLICATE_EVENT', 409)
    if rule.get('needs_active_passport') and not has_active_passport:
        raise DomainError(f'{event_type} requires an ACTIVE passport to supersede.', 'NO_ACTIVE_PASSPORT', 409)
    return rule


def relationship_label(parent_type, child_type):
    for p, c, label in HIERARCHY:
        if p == parent_type and c == child_type:
            return label
    raise DomainError(f'{parent_type} cannot directly contain/host {child_type}. Allowed: ' +
                      '; '.join(f'{p}→{c}' for p, c, _ in HIERARCHY), 'BAD_HIERARCHY', 409)
