"""Small read-only NVML binding, matching the installed NVIDIA nvml.h ABI.

No CUDA context is created. Process context membership is not GPU utilization.
"""
import ctypes as c
import os
from pathlib import Path


class MemoryInfo(c.Structure):
    _fields_ = [('total', c.c_ulonglong), ('free', c.c_ulonglong), ('used', c.c_ulonglong)]


class Utilization(c.Structure):
    _fields_ = [('gpu', c.c_uint), ('memory', c.c_uint)]


class ProcessInfo(c.Structure):
    _fields_ = [('pid', c.c_uint), ('usedGpuMemory', c.c_ulonglong), ('gpuInstanceId', c.c_uint), ('computeInstanceId', c.c_uint)]


class Nvidia:
    def __init__(self):
        self.lib = None
        self.reason = ''
        self.devices = []
        try:
            path = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/nvml.dll'
            self.lib = c.CDLL(str(path))
            self.call('nvmlInit_v2')
            count = c.c_uint()
            self.call('nvmlDeviceGetCount_v2', c.byref(count))
            for index in range(min(count.value, 4)):
                handle = c.c_void_p()
                self.call('nvmlDeviceGetHandleByIndex_v2', c.c_uint(index), c.byref(handle))
                self.devices.append(handle)
        except (OSError, AttributeError, RuntimeError) as exc:
            self.reason = str(exc)[:200]

    def call(self, name, *args):
        code = getattr(self.lib, name)(*args)
        if code:
            raise RuntimeError(f'{name}: NVML status {code}')

    def sample(self):
        output = []
        for index, handle in enumerate(self.devices):
            values, unavailable, contexts = {}, {}, {}
            queries = [('utilization', 'nvmlDeviceGetUtilizationRates', Utilization, ()),
                       ('memory', 'nvmlDeviceGetMemoryInfo', MemoryInfo, ()),
                       ('temperature_c', 'nvmlDeviceGetTemperature', c.c_uint, (c.c_uint(0),)),
                       ('power_w', 'nvmlDeviceGetPowerUsage', c.c_uint, ()),
                       ('clock_mhz', 'nvmlDeviceGetClockInfo', c.c_uint, (c.c_uint(0),))]
            for key, api, typ, extra in queries:
                result = typ()
                try:
                    self.call(api, handle, *extra, c.byref(result))
                    if key == 'utilization':
                        values['utilization_pct'] = (result.gpu, '%')
                    elif key == 'memory':
                        values.update(vram_used_bytes=(result.used, 'bytes'), vram_total_bytes=(result.total, 'bytes'))
                    else:
                        values[key] = (result.value / 1000 if key == 'power_w' else result.value, {'temperature_c': 'C', 'power_w': 'W', 'clock_mhz': 'MHz'}[key])
                except (RuntimeError, AttributeError) as exc:
                    unavailable[key] = str(exc)
            for kind in ('Compute', 'Graphics'):
                api = f'nvmlDeviceGet{kind}RunningProcesses_v3'
                try:
                    count = c.c_uint(256); array = (ProcessInfo * 256)()
                    self.call(api, handle, c.byref(count), array)
                    for item in array[:min(count.value, 256)]:
                        contexts.setdefault(item.pid, []).append(kind.lower())
                    # WDDM memory sentinel deliberately never converted to a measurement.
                except (RuntimeError, AttributeError) as exc:
                    unavailable[kind.lower() + '_processes'] = str(exc)
            output.append((index, values, unavailable, contexts))
        return output

    def close(self):
        if self.lib:
            try:
                self.call('nvmlShutdown')
            except (RuntimeError, AttributeError):
                pass
