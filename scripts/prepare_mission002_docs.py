"""Preserve Mission 001 documentation and generate the versioned schema contract."""
import copy
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
archive = root/'RELEASES/0.1.0-alpha.1'
archive.mkdir(exist_ok=True)
for name in ('README.md', 'ATOMVERSE-ARCHITECTURE.md', 'ATOMVERSE-FINAL-REPORT.md', 'ATOMVERSE-DATABASE-SCHEMA.md', 'ATOMVERSE-VISUALIZATION-SPEC.md'):
    target = archive/name
    if not target.exists():
        target.write_bytes((root/name).read_bytes())
legacy_path = root/'SPECIFICATIONS/EVENT-SCHEMA-1.0.json'
if not legacy_path.exists():
    legacy_path.write_bytes((root/'ATOMVERSE-EVENT-SCHEMA.json').read_bytes())
legacy = json.loads(legacy_path.read_text())
current = copy.deepcopy(legacy)
current['title'] = 'ATOMVERSE event 1.1'
current['properties']['schema_version'] = {'const': '1.1'}
current['required'].append('scientific')
classes = ['OBSERVED', 'DERIVED', 'AI_INTERPRETED', 'SIMULATED', 'UNAVAILABLE']
current['properties']['scientific'] = {
    'type': 'object', 'additionalProperties': False,
    'required': ['classification','session_id','entity_id','entity','relationships','metric_metadata','unavailable','retention'],
    'properties': {
        'classification': {'enum': classes}, 'session_id': {'type':'string','maxLength':160}, 'entity_id': {'type':'string','maxLength':160},
        'entity': {'type':'object'}, 'retention': {'enum':['rolling','protected']},
        'relationships': {'type':'array','maxItems':12,'items': {'type':'object','additionalProperties':False,'required':['type','target','source'],'properties': {k:{'type':'string','minLength':1,'maxLength':160} for k in ('type','target','source')}}},
        'metric_metadata': {'type':'object','maxProperties':32,'additionalProperties': {'type':'object','required':['classification'],'properties': {'classification': {'enum':classes},'formula': {'type':'string'},'inputs': {'type':'object'}}}},
        'unavailable': {'type':'object','additionalProperties': {'type':'string','minLength':1,'maxLength':500}}
    }
}
def units(node):
    if isinstance(node, dict):
        if node.get('enum') == ['%', 'ms', 's', 'bytes', 'MiB', 'count', 'C', 'GFLOP/s', 'ratio']:
            node['enum'] += ['W','MHz','bytes/s']
        for value in node.values(): units(value)
    elif isinstance(node, list):
        for value in node: units(value)
units(current)
# The runtime validates cross-field derivation consistency and encoded size as well.
(root/'ATOMVERSE-EVENT-SCHEMA.json').write_text(json.dumps({'$schema':'https://json-schema.org/draft/2020-12/schema','title':'ATOMVERSE events, legacy 1.0 and scientific 1.1','oneOf':[legacy,current]},indent=2)+'\n', encoding='utf-8')
