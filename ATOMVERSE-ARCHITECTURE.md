# ATOMVERSE architecture — 0.1.0-alpha.1

**Implemented vertical slice, Windows x64.** Stage 1 was remotely verified before source development; see [gate evidence](EVIDENCE/STAGE-1-VERIFICATION.json).

## Selected engines

Python 3.14 + Qt/PySide6 6.11 provides the native application, input controls, tables and a QPainter scene. The universe uses a mathematical 3D projection with rotation, zoom, pan and event selection. It is not a physics simulator or a hardware-instanced 3D engine. SQLite is embedded through Python's standard library. psutil and nvidia-smi supply explicitly requested observations. A separate Python process runs bounded matrix benchmarks; GPU operation consumes an existing PyTorch environment without installing or bundling CUDA/PyTorch.

Qt supports desktop packaging; SQLite is designed for independent local application storage. These capabilities and available local runtimes informed the decision. [Qt deployment](https://doc.qt.io/qtforpython-6.8/deployment/index.html), [SQLite applications](https://www.sqlite.org/whentouse.html).

## Modules and contracts

| Module | Interface | Responsibility |
|---|---|---|
| core.py | make_event / validate_event | Version 1.0 schema, timestamps, units, finite values, 8 KiB event limit |
| adapters.py | import_events(path) → list[event] | Explicit ARX 0.1 or ATOMVERSE export intake, 96 MiB file bound |
| core.py | derive(metrics, status, category, confidence, scale) | Reproducible dimensionless normalization and status color |
| core.py | Memory.add / events / close | Atomic transactions, immutable IDs, chronological readback |
| core.py | Replay.seek(count) | Recorded order, no new observations |
| core.py | export_events | Atomic JSON and formula-protected CSV |
| sources.py | sample_hardware | Requested CPU/RAM and NVIDIA observations |
| sources.py | inspect_repository | Explicit directory metadata, no content execution |
| sources.py | explain_local | Operator-requested loopback chat API; labeled interpretation |
| worker.py | JSON-lines progress/result protocol | CPU float matrix and optional synchronized CUDA matrix |
| benchmark.py | start / cancel / completed | One worker, 30-second wall limit, accurate outcome |
| scene.py | set_events / selected | Bounded projected universe with event identity |
| app.py | Window | Ten navigation destinations, source permissions and lifecycle |

One asynchronous source task is allowed at a time. The main thread owns SQLite and widgets. The benchmark is a separate process. No local web server, database service, external account or model is required to launch.

## Lifecycle and limits

Live polling is off at startup. Explicit enablement samples every two seconds, skips overlapping work, and stops on close or mode changes. Benchmarks allow 0.1–3 seconds of measured kernel work and 30 seconds total wall time, including startup. CPU dimensions are 8–64; GPU dimensions 128–1024. GPU admission reserves 1536 MiB free VRAM and limits the PyTorch allocator fraction to 20%. This is a conservative admission policy, not a guarantee about changing load from other applications.

Rendering defaults to 30 FPS and 256 particles, supports 15/30/60 FPS and 32–512 particles, reduces to 15 FPS during benchmarks, and automatically reduces rendered detail when frame work exceeds the budget. Measurements remain in the database. Object inspection and measurements do not require a running model.

Memory stops accepting new events at 10,000 records or the SQLite page limit (256 MiB with its default page size). It does not silently delete history. Export history and choose a fresh data directory at capacity. Temporary atomic exports and SQLite rollback journals may temporarily use additional disk space.

## Epistemic boundaries

Observed records persist; synthetic demonstration records stay in memory and never enter real intake. AI responses are labeled interpretations and cannot invoke tools. Raw measurements are unchanged by rendering settings. An ARX inventory capacity score describes capacity, not measured workload. Missing readings remain absent.

A benchmark result includes configuration, runtime versions, duration, iterations, checksum and verification outcome. Timing includes synchronized per-iteration host overhead and is not a vendor peak-throughput claim. Different CPU and GPU kernels are not directly comparable.

## Packaging

The portable Windows folder contains ATOMVERSE-AI.exe and its adjacent _internal dependencies. It is an unsigned development build. The GPU environment remains external and selectable. No installer or system services are added. See [build guide](SOFTWARE/README.md), [verification](EVIDENCE/ATOMVERSE-GUI-VERIFICATION.json) and [limitations](ATOMVERSE-FINAL-REPORT.md).
