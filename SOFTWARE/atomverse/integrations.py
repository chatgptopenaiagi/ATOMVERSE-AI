"""Explicit, versioned read-only exports from independent engineering projects."""
import hashlib
from pathlib import Path
from .adapters import import_events
from .core import decode_json, MAX_FILE, ValidationError, utc
from .science import record

COG_CATEGORIES = ('Application', 'Codex', 'PowerShell', 'Browser', 'Authentication', 'Github', 'Vault', 'System', 'Recovery', 'Settings')
COG_OUTCOMES = ('Started', 'Ready', 'NeedsAttention', 'Completed', 'Failed', 'Cancelled', 'RolledBack', 'Cleared', 'ConfigurationChanged')
DRAGON_STATES = ('not_implemented', 'installed_not_configured', 'configured_unverified', 'ready', 'degraded', 'unavailable', 'not_applicable')


def import_selected(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_FILE + 1)
    data = decode_json(raw)
    if not isinstance(data, dict):
        raise ValidationError('Engine export must be a JSON object')
    if data.get('version') == '2.0.0' and 'events' in data:
        sha = hashlib.sha256(raw).hexdigest()
        rows = data['events']
        if not isinstance(rows, list) or len(rows) > 200:
            raise ValidationError('COG export event limit is 200')
        events = []
        for i, row in enumerate(rows):
            if not isinstance(row, dict) or type(row.get('Category')) is not int or type(row.get('Outcome')) is not int or not 0 <= row['Category'] < len(COG_CATEGORIES) or not 0 <= row['Outcome'] < len(COG_OUTCOMES):
                raise ValidationError('Invalid COG diagnostic enum')
            outcome = COG_OUTCOMES[row['Outcome']]
            e = record('COG explicit export/2.0.0', 'guardian', 'integration:cog', category='integration', rolling=False,
                timestamp=utc(row['Timestamp']), status='FAIL' if outcome == 'Failed' else 'CANCELLED' if outcome == 'Cancelled' else 'INFO',
                message=f'{COG_CATEGORIES[row["Category"]]}: {outcome}. Reported by COG; not independently rerun.',
                provenance={'file_sha256': sha, 'row': i, 'producer_version': '2.0.0'})
            e['event_id'] = f'cog:{sha[:32]}:{i}'; events.append(e)
        return events
    if 'registry_version' in data:
        if data.get('schema_version') != 1 or data['registry_version'] != 'module-registry/1' or data.get('read_only') is not True:
            raise ValidationError('Unsupported DRAGONHYDRA snapshot version or read-only flag')
        rows = data.get('modules')
        if not isinstance(rows, list) or len(rows) > 128:
            raise ValidationError('DRAGONHYDRA module limit is 128')
        sha = hashlib.sha256(raw).hexdigest(); events = []
        for i, row in enumerate(rows):
            try:
                definition, observation = row['definition'], row['observation']
                module_id, state = definition['module_id'], observation['runtime_state']
                if state not in DRAGON_STATES or not isinstance(module_id, str) or len(module_id) > 100:
                    raise ValueError()
            except (KeyError, TypeError, ValueError):
                raise ValidationError('Invalid DRAGONHYDRA module observation')
            e = record('DRAGONHYDRA module-registry/1', 'guardian', 'integration:dragon:' + module_id,
                category='integration', rolling=False, timestamp=utc(data['as_of']),
                status='SKIP' if state in ('unavailable', 'not_implemented') else 'INFO',
                message=f'{module_id}: {state}. Historical producer report; not a current readiness guarantee.',
                provenance={'file_sha256': sha, 'row': i, 'registry_version': 'module-registry/1'})
            e['event_id'] = f'dragon:{sha[:32]}:{i}'; events.append(e)
        return events
    return import_events(path)
