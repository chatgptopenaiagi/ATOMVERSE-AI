"""Bounded Windows observation. No command lines, environment, or file contents."""
import ctypes as c
import hashlib
import os
import time
from dataclasses import dataclass, asdict
import psutil
from .core import metric, utc_now, ValidationError
from .science import record, derived
from .nvml import Nvidia


@dataclass
class ObserverConfig:
    interval_s: float = 2.0
    process_limit: int = 24
    processes: bool = True
    gpu: bool = True
    max_rows: int = 10000
    retention_hours: float = 1.0

    def validate(self):
        if not 0.5 <= self.interval_s <= 30 or not 1 <= self.process_limit <= 64 or not 100 <= self.max_rows <= 10000 or not 0.01 <= self.retention_hours <= 720:
            raise ValidationError('observer configuration exceeds supported bounds')
        if type(self.processes) is not bool or type(self.gpu) is not bool:
            raise ValidationError('source permissions must be boolean')
        return asdict(self)


def process_identity(pid, created):
    return f'process:{pid}@{created:.6f}'


def cpu_delta(before, after):
    total = sum(after) - sum(before)
    idle = after[2] - before[2]
    if total <= 0 or idle < 0 or any(b > a for b, a in zip(before, after)):
        return None
    return min(100.0, max(0.0, 100 * (total - idle) / total)), derived(
        'clamp(100 * (delta_total_s - delta_idle_s) / delta_total_s, 0, 100)',
        previous_user_system_idle=list(before), current_user_system_idle=list(after), delta_total_s=total, delta_idle_s=idle)


def committed_memory():
    class PerformanceInfo(c.Structure):
        _fields_ = [('cb', c.c_ulong)] + [(k, c.c_size_t) for k in ('CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal', 'PhysicalAvailable', 'SystemCache', 'KernelTotal', 'KernelPaged', 'KernelNonpaged', 'PageSize')] + [(k, c.c_ulong) for k in ('HandleCount', 'ProcessCount', 'ThreadCount')]
    info = PerformanceInfo(); info.cb = c.sizeof(info)
    if not c.windll.psapi.GetPerformanceInfo(c.byref(info), info.cb):
        raise OSError('GetPerformanceInfo failed')
    return info.CommitTotal * info.PageSize, info.CommitLimit * info.PageSize


def parent_snapshot():
    """One Toolhelp snapshot, instead of rebuilding the PID map for every process."""
    from ctypes import wintypes as w
    class Entry(c.Structure):
        _fields_ = [('dwSize', w.DWORD), ('cntUsage', w.DWORD), ('th32ProcessID', w.DWORD),
                    ('th32DefaultHeapID', c.c_size_t), ('th32ModuleID', w.DWORD), ('cntThreads', w.DWORD),
                    ('th32ParentProcessID', w.DWORD), ('pcPriClassBase', w.LONG), ('dwFlags', w.DWORD), ('szExeFile', w.WCHAR * 260)]
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = w.HANDLE
    kernel.Process32FirstW.argtypes = kernel.Process32NextW.argtypes = [w.HANDLE, c.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == c.c_void_p(-1).value:
        raise OSError('Toolhelp process snapshot unavailable')
    entry = Entry(); entry.dwSize = c.sizeof(entry); result = {}
    try:
        valid = kernel.Process32FirstW(handle, c.byref(entry))
        while valid and len(result) < 32768:
            result[entry.th32ProcessID] = entry.th32ParentProcessID
            valid = kernel.Process32NextW(handle, c.byref(entry))
    finally:
        kernel.CloseHandle(handle)
    return result


class Collector:
    def __init__(self, config, session, gui_pid=None):
        config.validate()
        self.config, self.session, self.gui_pid = config, session, gui_pid
        self.nvidia = Nvidia() if config.gpu else None
        self.previous_cpu = None
        self.previous_disk = None
        self.previous_net = None
        self.previous_processes = {}
        self.tracked = {}
        self.previous_time = None
        self.previous_own = None

    def sample(self):
        started = time.perf_counter(); stamp = utc_now()
        elapsed = started - self.previous_time if self.previous_time else None
        events = []
        def add(source, component, entity_id, values=None, **kwargs):
            e = record(source, component, entity_id, values, session=self.session, timestamp=stamp, **kwargs)
            e['configuration'] = {'sampling_interval_s': self.config.interval_s}
            events.append(e)
            return e
        cpus = [(t.user, t.system, t.idle) for t in psutil.cpu_times(percpu=True)][:256]
        frequency = psutil.cpu_freq()
        totals = tuple(sum(t[i] for t in cpus) for i in range(3))
        all_cpu = [totals] + cpus
        for index, counters in enumerate(all_cpu):
            values, meta = {}, {}
            entity = 'system:cpu' if index == 0 else f'cpu:{index - 1}'
            if self.previous_cpu and index < len(self.previous_cpu):
                result = cpu_delta(self.previous_cpu[index], counters)
                if result:
                    values['utilization_pct'] = metric(result[0], '%'); meta['utilization_pct'] = result[1]
            if index == 0:
                values['logical_processors'] = metric(len(cpus), 'count'); meta['logical_processors'] = {'classification': 'OBSERVED'}
                if frequency:
                    values['frequency_mhz'] = metric(frequency.current, 'MHz'); meta['frequency_mhz'] = {'classification': 'OBSERVED'}
            add('psutil.cpu_times/Windows', 'cpu', entity, values, metadata=meta,
                cls='DERIVED' if 'utilization_pct' in values else 'OBSERVED',
                unavailable={'temperature_c': 'No verified CPU temperature sensor', **({'utilization_pct': 'First sample or counter reset; a second sample is required'} if 'utilization_pct' not in values else {})},
                entity={'type': 'cpu' if index == 0 else 'cpu_core', 'logical_index': index - 1},
                provenance={'api': 'GetSystemTimes / NtQuerySystemInformation via psutil', 'psutil_version': psutil.__version__})
        self.previous_cpu = all_cpu
        ram = psutil.virtual_memory()
        values = {'total_bytes': metric(ram.total, 'bytes'), 'available_bytes': metric(ram.available, 'bytes'), 'used_pct': metric(100 * (ram.total - ram.available) / ram.total, '%')}
        meta = {k: {'classification': 'OBSERVED'} for k in values}
        meta['used_pct'] = derived('100 * (total_bytes - available_bytes) / total_bytes', total_bytes=ram.total, available_bytes=ram.available)
        missing = {}
        try:
            committed, limit = committed_memory()
            values.update(committed_bytes=metric(committed, 'bytes'), commit_limit_bytes=metric(limit, 'bytes'))
            meta.update({k: {'classification': 'OBSERVED'} for k in ('committed_bytes', 'commit_limit_bytes')})
        except (OSError, AttributeError) as exc:
            missing['committed_bytes'] = str(exc)
        add('psutil / Windows GetPerformanceInfo', 'memory', 'system:memory', values, metadata=meta, unavailable=missing)
        disk = psutil.disk_io_counters()
        if disk:
            values = {k: metric(getattr(disk, k), 'bytes' if k.endswith('bytes') else 'count') for k in ('read_bytes', 'write_bytes', 'read_count', 'write_count')}
            meta = {k: {'classification': 'OBSERVED'} for k in values}
            try:
                volume = psutil.disk_usage(os.environ.get('SystemDrive', 'C:') + os.sep)
                values.update(volume_total_bytes=metric(volume.total, 'bytes'), volume_free_bytes=metric(volume.free, 'bytes'), used_pct=metric(100 * volume.used / volume.total, '%'))
                meta.update(volume_total_bytes={'classification': 'OBSERVED'}, volume_free_bytes={'classification': 'OBSERVED'}, used_pct=derived('100 * used_bytes / total_bytes', used_bytes=volume.used, total_bytes=volume.total))
            except OSError:
                pass
            if elapsed and self.previous_disk:
                for direction in ('read', 'write'):
                    delta = getattr(disk, direction + '_bytes') - getattr(self.previous_disk, direction + '_bytes')
                    if delta >= 0:
                        key = direction + '_bytes_per_s'; values[key] = metric(delta / elapsed, 'bytes/s'); meta[key] = derived('delta_bytes / elapsed_s', delta_bytes=delta, elapsed_s=elapsed)
            add('psutil.disk_io_counters/Windows', 'storage', 'system:storage', values, metadata=meta,
                unavailable={'response_time_ms': 'Aggregate disk latency is not verified by this collector'}, message='Aggregate disk counters; throughput is a counter-delta calculation.')
            self.previous_disk = disk
        else:
            add('psutil.disk_io_counters/Windows', 'storage', 'system:storage', cls='UNAVAILABLE', unavailable={'disk': 'Windows disk counters unavailable'})
        gpu_contexts = {}
        self.gpu_observed_at = time.time()
        if self.nvidia:
            samples = self.nvidia.sample()
            if not samples:
                add('NVIDIA NVML', 'gpu', 'gpu:0', cls='UNAVAILABLE', unavailable={'gpu': self.nvidia.reason or 'No NVIDIA devices'})
            for index, values, missing, contexts in samples:
                add('NVIDIA NVML', 'gpu', f'gpu:{index}', {k: metric(*v) for k, v in values.items()}, unavailable=missing,
                    message='Device-wide measurements. GPU activity does not imply AI activity.', provenance={'api': 'NVML; no CUDA context created', 'scope': 'device'})
                for pid, kinds in contexts.items():
                    gpu_contexts.setdefault(pid, []).append((index, kinds))
        if self.config.processes:
            self.sample_processes(add, elapsed, gpu_contexts)
        own_cpu, rss = 0.0, 0
        for pid in {os.getpid(), self.gui_pid} - {None}:
            try:
                p = psutil.Process(pid); times = p.cpu_times(); own_cpu += times.user + times.system; rss += p.memory_info().rss
            except psutil.Error:
                pass
        values = {'working_set_bytes': metric(rss, 'bytes'), 'collection_ms': metric((time.perf_counter() - started) * 1000, 'ms')}
        meta = {k: {'classification': 'OBSERVED'} for k in values}
        if self.previous_own is not None and elapsed and own_cpu >= self.previous_own:
            values['utilization_pct'] = metric(min(100, (own_cpu - self.previous_own) / elapsed / len(cpus) * 100), '%')
            meta['utilization_pct'] = derived('100 * delta_process_cpu_s / elapsed_s / logical_processors', delta_process_cpu_s=own_cpu - self.previous_own, elapsed_s=elapsed, logical_processors=len(cpus))
        add('ATOMVERSE self-observation', 'guardian', 'atomverse:overhead', values, metadata=meta,
            message='Combined GUI and observer working sets and CPU; excludes optional benchmark and AI workers.')
        self.previous_own, self.previous_time = own_cpu, started
        return events

    def sample_processes(self, add, elapsed, gpu_contexts):
        pids = psutil.pids()
        selected, inaccessible = [], 0
        # Maximum 512 process probes per sample. Prefer our process to keep overhead observable.
        candidates = list(dict.fromkeys([os.getpid(), self.gui_pid] + pids))
        for pid in candidates[:512]:
            if pid is None:
                continue
            try:
                p = psutil.Process(pid)
                with p.oneshot():
                    created = p.create_time(); times = p.cpu_times(); mem = p.memory_info()
                    item = {'pid': pid, 'created': created, 'name': p.name()[:120], 'rss': mem.rss, 'cpu': times.user + times.system}
                selected.append(item)
            except (psutil.Error, OSError):
                inaccessible += 1
        selected.sort(key=lambda p: (p['pid'] in (os.getpid(), self.gui_pid), p['rss']), reverse=True)
        selected = selected[:self.config.process_limit]
        # Capture relationships between two identity checks to exclude PID reuse races.
        try:
            parents = parent_snapshot()
        except OSError:
            parents = {}
        current = {}
        for item in selected:
            pid, created = item['pid'], item['created']; identity = process_identity(pid, created)
            relations = [{'type': 'USES_CPU', 'target': 'system:cpu', 'source': 'psutil.Process.cpu_times'}, {'type': 'USES_MEMORY', 'target': 'system:memory', 'source': 'psutil.Process.memory_info'}]
            entity = {'type': 'process', 'pid': pid, 'created_unix_s': created, 'name': item['name'], 'state': 'active_at_timestamp'}
            try:
                p = psutil.Process(pid)
                if p.create_time() != created:
                    continue
                executable = p.exe()
                if executable:
                    eid = 'executable:' + hashlib.sha256(os.path.normcase(executable).encode()).hexdigest()[:24]
                    relations.append({'type': 'EXECUTABLE', 'target': eid, 'source': 'psutil.Process.exe; path hashed'})
                    entity['executable_name'] = os.path.basename(executable)[:120]
                parent = psutil.Process(parents[pid]) if parents.get(pid) else None
                if parent and parent.create_time() <= created:
                    relations.append({'type': 'PARENT', 'target': process_identity(parent.pid, parent.create_time()), 'source': 'Windows parent PID + creation-time check'})
            except (psutil.Error, OSError):
                pass
            for index, kinds in gpu_contexts.get(pid, []) if created <= self.gpu_observed_at else []:
                relations.append({'type': 'GPU_CONTEXT', 'target': f'gpu:{index}', 'source': 'NVML ' + '/'.join(kinds) + ' context list; no utilization attribution'})
            values = {'working_set_bytes': metric(item['rss'], 'bytes'), 'cpu_time_s': metric(item['cpu'], 's')}
            meta = {k: {'classification': 'OBSERVED'} for k in values}
            old = self.previous_processes.get(identity)
            if old is not None and elapsed and item['cpu'] >= old:
                values['utilization_pct'] = metric(min(100, 100 * (item['cpu'] - old) / elapsed / (psutil.cpu_count() or 1)), '%')
                meta['utilization_pct'] = derived('100 * delta_cpu_s / elapsed_s / logical_processors', delta_cpu_s=item['cpu'] - old, elapsed_s=elapsed, logical_processors=psutil.cpu_count() or 1)
            add('psutil.Process/Windows', 'code', identity, values, metadata=meta, entity=entity, relationships=relations,
                unavailable={'gpu_utilization_pct': 'No reliable per-process utilization attribution', 'gpu_memory_bytes': 'Not collected; WDDM allocation is not reliable through NVML'},
                message='Observed process metadata only. Name and working set are local data; review before export.')
            current[identity] = item['cpu']; self.tracked[identity] = entity
        # Absence from our bounded selection is NOT termination.
        for identity, entity in list(self.tracked.items()):
            if identity in current:
                continue
            terminated = entity['pid'] not in pids
            if not terminated:
                try:
                    terminated = psutil.Process(entity['pid']).create_time() != entity['created_unix_s']
                except psutil.NoSuchProcess:
                    terminated = True
                except psutil.AccessDenied:
                    pass
            if terminated:
                add('psutil.Process/Windows', 'code', identity, entity={**entity, 'state': 'terminated'}, category='process_exit', message='Previously observed identity no longer exists; this is detection time, not exact exit time.')
                del self.tracked[identity]
        self.tracked = dict(list(self.tracked.items())[-256:])
        self.previous_processes = current
        add('ATOMVERSE observer coverage', 'guardian', 'observer:coverage',
            {'enumerated_processes': metric(len(pids), 'count'), 'sampled_processes': metric(len(current), 'count'), 'inaccessible_processes': metric(inaccessible, 'count')},
            message='Bounded selection: highest working sets among up to 512 probed PIDs, plus ATOMVERSE. Omitted processes are not presumed terminated.')

    def close(self):
        if self.nvidia:
            self.nvidia.close()
