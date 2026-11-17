"""Versioned scientific metadata; legacy 1.0 event bodies remain unchanged."""
import copy
import json
from .core import ValidationError, make_event, validate_event, MAX_EVENT

CLASSES = ('OBSERVED', 'DERIVED', 'AI_INTERPRETED', 'SIMULATED', 'UNAVAILABLE')
KINDS = {'OBSERVED': 'observed', 'DERIVED': 'observed', 'UNAVAILABLE': 'observed',
         'AI_INTERPRETED': 'interpretation', 'SIMULATED': 'synthetic'}
COLORS = {'OBSERVED': '#65baff', 'DERIVED': '#68e4b0', 'AI_INTERPRETED': '#d69bff',
          'SIMULATED': '#ffca78', 'UNAVAILABLE': '#8292ab'}


def classification(event, metric_name=None):
    s = event.get('scientific', {})
    if metric_name in s.get('metric_metadata', {}):
        return s['metric_metadata'][metric_name]['classification']
    return s.get('classification', {'observed': 'OBSERVED', 'synthetic': 'SIMULATED', 'interpretation': 'AI_INTERPRETED'}[event['data_kind']])


def record(source, component, entity_id, metrics=None, *, category='observation', cls='OBSERVED',
           session='', metadata=None, unavailable=None, entity=None, relationships=None,
           message='', status='INFO', provenance=None, timestamp=None, rolling=True):
    e = make_event(source, category, component, metrics, kind=KINDS[cls], message=message,
                   status=status, provenance=provenance, timestamp=timestamp)
    e['schema_version'] = '1.1'
    e['scientific'] = {'classification': cls, 'session_id': session, 'entity_id': entity_id,
                      'entity': entity or {}, 'relationships': relationships or [],
                      'metric_metadata': metadata or {k: {'classification': cls} for k in e['metrics']},
                      'unavailable': unavailable or {}, 'retention': 'rolling' if rolling else 'protected'}
    return validate_scientific(e)


def validate_scientific(event):
    e = copy.deepcopy(event)
    s = e.pop('scientific', None)
    if not isinstance(s, dict) or set(s) != {'classification', 'session_id', 'entity_id', 'entity', 'relationships', 'metric_metadata', 'unavailable', 'retention'}:
        raise ValidationError('schema 1.1 requires complete scientific metadata')
    if s['classification'] not in CLASSES or e.get('data_kind') != KINDS[s['classification']]:
        raise ValidationError('scientific classification conflicts with data kind')
    if s['retention'] not in ('rolling', 'protected'):
        raise ValidationError('invalid retention policy')
    for key in ('entity_id', 'session_id'):
        if not isinstance(s[key], str) or len(s[key]) > 160:
            raise ValidationError('invalid scientific identity')
    for key in ('entity', 'metric_metadata', 'unavailable'):
        if not isinstance(s[key], dict):
            raise ValidationError('scientific mappings must be objects')
    entity = s['entity']
    if entity.get('type') == 'process':
        if type(entity.get('pid')) is not int or entity['pid'] < 0 or type(entity.get('created_unix_s')) not in (int, float) or entity['created_unix_s'] < 0 or entity.get('state') not in ('active_at_timestamp', 'terminated'):
            raise ValidationError('process entity requires PID, creation time and observation state')
        if 'name' in entity and (not isinstance(entity['name'], str) or len(entity['name']) > 120):
            raise ValidationError('invalid process name')
    if entity.get('type') == 'cpu_core' and (type(entity.get('logical_index')) is not int or not 0 <= entity['logical_index'] < 256):
        raise ValidationError('CPU core requires a bounded logical index')
    if set(s['metric_metadata']) != set(e.get('metrics', {})):
        raise ValidationError('every metric requires a classification')
    for m in s['metric_metadata'].values():
        if not isinstance(m, dict) or m.get('classification') not in CLASSES:
            raise ValidationError('invalid metric classification')
        if m['classification'] in ('UNAVAILABLE', 'AI_INTERPRETED'):
            raise ValidationError('unavailable and AI text cannot be numerical measurements')
        if s['classification'] == 'SIMULATED' and m['classification'] != 'SIMULATED':
            raise ValidationError('simulated data cannot contain observed measurements')
        if s['classification'] in ('OBSERVED', 'DERIVED') and m['classification'] not in ('OBSERVED', 'DERIVED'):
            raise ValidationError('observed workspace cannot contain simulated measurements')
        if m['classification'] == 'DERIVED' and (not isinstance(m.get('inputs'), dict) or not isinstance(m.get('formula'), str) or not m['formula']):
            raise ValidationError('derived metric requires inputs and formula')
    if s['classification'] in ('UNAVAILABLE', 'AI_INTERPRETED') and e.get('metrics'):
        raise ValidationError('unavailable or AI event must not contain measurements')
    if any(not isinstance(v, str) or not v or len(v) > 500 for v in s['unavailable'].values()):
        raise ValidationError('unavailable metrics require bounded reasons')
    if not isinstance(s['relationships'], list) or len(s['relationships']) > 12:
        raise ValidationError('relationship limit exceeded')
    for rel in s['relationships']:
        if not isinstance(rel, dict) or set(rel) != {'type', 'target', 'source'} or any(not isinstance(v, str) or not v or len(v) > 160 for v in rel.values()):
            raise ValidationError('relationship requires type, target and source')
    e['schema_version'] = '1.0'
    validate_event(e)
    if len(json.dumps(event, allow_nan=False).encode()) > MAX_EVENT:
        raise ValidationError('event exceeds 8 KiB')
    return copy.deepcopy(event)


def derived(formula, **inputs):
    return {'classification': 'DERIVED', 'formula': formula, 'inputs': inputs}
