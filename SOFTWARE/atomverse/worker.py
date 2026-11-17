"""Standalone bounded benchmark worker. No GUI or global environment changes."""
import argparse
import json
import math
import platform
import sys
import time


def send(kind, **data):
    print(json.dumps({'type': kind, **data}, allow_nan=False), flush=True)


def run(kind, seconds, size):
    if kind not in ('cpu', 'gpu') or not 0.1 <= seconds <= 3.0:
        raise ValueError('benchmark duration must be 0.1 to 3 seconds')
    if kind == 'cpu' and not 8 <= size <= 64 or kind == 'gpu' and not 128 <= size <= 1024:
        raise ValueError('workload size exceeds the bounded policy')
    config = {'kind': kind, 'seconds': seconds, 'size': size, 'dtype': 'float32' if kind == 'gpu' else 'python-float', 'python': platform.python_version(), 'warmup_iterations': 1, 'max_wall_seconds': 30}
    if kind == 'cpu':
        a = [[float((i + k) % 7) for k in range(size)] for i in range(size)]
        b = [[1.0] * size for _ in range(size)]
        def operation():
            return [[sum(a[i][k] * b[k][j] for k in range(size)) for j in range(size)] for i in range(size)]
        expected = [sum(row) for row in a]
        operation()
        sync = lambda: None
        config.update(backend='stdlib-matrix', device=platform.machine(), processor=platform.processor(), synchronized=True, threads=1)
    else:
        import torch
        if not torch.cuda.is_available():
            send('result', status='SKIP', message='CUDA unavailable in selected interpreter', metrics={}, configuration=config)
            return
        free, total = torch.cuda.mem_get_info()
        required = 3 * size * size * 4
        if free < 1536 * 1024**2 + required or required > 64 * 1024**2:
            send('result', status='SKIP', message='Insufficient VRAM headroom: 1536 MiB reserve required', metrics={}, configuration=config)
            return
        torch.cuda.set_per_process_memory_fraction(0.2)
        torch.set_float32_matmul_precision('highest')
        a = torch.ones((size, size), dtype=torch.float32, device='cuda')
        b = torch.eye(size, dtype=torch.float32, device='cuda')
        def operation():
            return a @ b
        sync = torch.cuda.synchronize
        operation()
        sync()
        config.update(backend='pytorch', torch=torch.__version__, cuda=torch.version.cuda,
                      cudnn=torch.backends.cudnn.version(), device=torch.cuda.get_device_name(0),
                      synchronized=True, vram_reserve_mib=1536, tensor_bytes=required, tf32=False)
    iterations, last = 0, 0.0
    start = time.perf_counter()
    while True:
        output = operation()
        sync()
        iterations += 1
        elapsed = time.perf_counter() - start
        if elapsed - last >= 0.2:
            send('progress', elapsed_s=elapsed, iterations=iterations, fraction=min(1, elapsed / seconds))
            last = elapsed
        if elapsed >= seconds:
            break
    if kind == 'cpu':
        verified = all(value == expected[i] for i, row in enumerate(output) for value in row)
        checksum = sum(map(sum, output))
    else:
        verified = bool(torch.allclose(output, a, rtol=0, atol=1e-6))
        checksum = float(output.sum().item())
    metrics = {'duration_ms': {'value': elapsed * 1000, 'unit': 'ms'},
               'iterations': {'value': iterations, 'unit': 'count'},
               'mean_iteration_ms': {'value': elapsed * 1000 / iterations, 'unit': 'ms'},
               'throughput_gflops': {'value': 2 * size**3 * iterations / elapsed / 1e9, 'unit': 'GFLOP/s'},
               'checksum': {'value': checksum, 'unit': 'count'}}
    if kind == 'gpu':
        metrics['allocated_peak_mib'] = {'value': torch.cuda.max_memory_allocated() / 1024**2, 'unit': 'MiB'}
    send('result', status='PASS' if verified else 'FAIL', message='Matrix output numerically verified' if verified else 'Matrix verification failed', metrics=metrics, configuration=config)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['cpu', 'gpu'])
    parser.add_argument('--seconds', type=float, default=1.0)
    parser.add_argument('--size', type=int, default=32)
    args = parser.parse_args(argv)
    try:
        run(args.kind, args.seconds, args.size)
    except Exception as exc:
        send('result', status='FAIL', message=f'{type(exc).__name__}: {str(exc)[:1000]}', metrics={}, configuration={'kind': args.kind, 'seconds': args.seconds, 'size': args.size})
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
