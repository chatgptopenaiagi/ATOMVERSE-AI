"""Read-only ARX schema 0.1 and explicit ATOMVERSE event imports."""
import hashlib
import json
from pathlib import Path
from .core import ValidationError, make_event, metric, decode_json, validate_event, utc, MAX_FILE


def arx_events(report, source_hash):
    if not isinstance(report, dict) or report.get('schema_version') != '0.1':
        raise ValidationError('ARX requires machine-report envelope 0.1; Project DNA 0.2 is not supported')
    if (report.get('scanner') or {}).get('name') != 'ARX' or not isinstance(report.get('machine'), dict):
        raise ValidationError('expected an ARX scanner and machine object')
    machine = report['machine']
    stamp = utc(report.get('generated_at') or machine.get('generated_at'))
    result = []

    def emit(key, component, measurements, message, detail=None):
        # A stable file hash and JSON pointer make repeated imports idempotent.
        result.append(make_event('ARX', 'inventory', component, measurements, timestamp=stamp,
            event_id=hashlib.sha256((source_hash + key).encode()).hexdigest(), message=message[:1800],
            provenance={'sha256': source_hash, 'pointer': '/machine/' + key, 'arx_schema': '0.1',
                        'scanner_version': str(report['scanner'].get('version', 'unknown'))[:80]},
            configuration=detail or {}))

    cpu = machine.get('cpu') or {}
    if not isinstance(cpu, dict):
        raise ValidationError('ARX cpu must be an object')
    cm = {}
    for field, key in [('NumberOfCores', 'cores'), ('NumberOfLogicalProcessors', 'logical_processors'), ('logical_processors', 'logical_processors')]:
        if cpu.get(field) is not None:
            cm[key] = metric(cpu[field], 'count')
    if cpu:
        emit('cpu', 'cpu', cm, str(cpu.get('Name') or cpu.get('model') or 'CPU inventory'))
    mem = machine.get('memory') or {}
    if not isinstance(mem, dict):
        raise ValidationError('ARX memory must be an object')
    mm = {k: metric(mem[k], 'bytes') for k in ('total_bytes', 'available_bytes') if mem.get(k) is not None}
    if mm:
        emit('memory', 'memory', mm, 'ARX RAM snapshot; visual score represents reported capacity, not workload')
    gpus = machine.get('gpu') or []
    if isinstance(gpus, dict):
        gpus = [gpus]
    if not isinstance(gpus, list) or len(gpus) > 32:
        raise ValidationError('invalid ARX GPU list')
    for i, gpu in enumerate(gpus):
        if not isinstance(gpu, dict):
            raise ValidationError('invalid GPU record')
        # Win32 AdapterRAM is a 32-bit field; deliberately do not present it as accurate VRAM.
        emit(f'gpu/{i}', 'gpu', {}, str(gpu.get('Name') or 'GPU inventory'), {'driver': str(gpu.get('DriverVersion', 'unknown'))[:100], 'vram_note': 'CIM AdapterRAM omitted: unreliable above 4 GiB'})
    compute = machine.get('gpu_compute') or {}
    if not isinstance(compute, dict) or compute and compute.get('schema_version') != '1.0':
        raise ValidationError('unsupported ARX gpu_compute schema; expected 1.0')
    for i, gpu in enumerate((compute.get('nvidia_tooling_gpus') or [])[:32]):
        if not isinstance(gpu, dict):
            raise ValidationError('invalid NVIDIA tooling GPU record')
        if gpu.get('dedicated_vram_bytes') is not None:
            emit(f'gpu_compute/nvidia_tooling_gpus/{i}', 'gpu', {'total_bytes': metric(gpu['dedicated_vram_bytes'], 'bytes')},
                 str(gpu.get('name') or 'NVIDIA GPU') + ' — NVIDIA tooling VRAM capacity',
                 {'compute_capability': str(gpu.get('compute_capability', 'unknown'))[:30], 'driver': str(gpu.get('driver_version', 'unknown'))[:80]})
    storage = machine.get('storage') or []
    if isinstance(storage, dict):
        storage = [storage]
    if not isinstance(storage, list) or len(storage) > 64:
        raise ValidationError('invalid storage list')
    for i, disk in enumerate(storage):
        if not isinstance(disk, dict):
            raise ValidationError('invalid storage record')
        dm = {key: metric(disk[field], 'bytes') for field, key in [('Size', 'total_bytes'), ('SizeRemaining', 'available_bytes')] if disk.get(field) is not None}
        if dm:
            emit(f'storage/{i}', 'storage', dm, 'Storage volume ' + str(disk.get('DriveLetter', '?'))[:4])
    tools = machine.get('tools') or {}
    if not isinstance(tools, dict) or len(tools) > 128:
        raise ValidationError('invalid tools inventory')
    for name, tool in tools.items():
        if not isinstance(tool, dict):
            continue
        emit(f'tools/{name}', 'code', {}, f'{name}: inventory observation',
             {'detected': tool.get('detected'), 'available': tool.get('available'), 'version': str(tool.get('version') or 'unknown')[:300]})
    if not result:
        raise ValidationError('ARX report has no supported hardware or tool fields')
    return result


def import_events(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_FILE + 1)
    data = decode_json(raw)
    digest = hashlib.sha256(raw).hexdigest()
    if isinstance(data, dict) and data.get('format') == 'atomverse-export/1':
        rows = data.get('events')
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValidationError('invalid export event list')
        return [validate_event(e) for e in rows]
    return arx_events(data, digest)
