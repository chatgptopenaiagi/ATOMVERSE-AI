# Implemented visualization specification

The nucleus represents the workstation; eight rings represent CPU, GPU, memory, storage, AI, code, database and Guardian. All rings are navigational structures. Data particles exist only for events in the current mode. Background stars are decorative and carry no measurements.

For the first supported metric in core.METRIC_RANGES:

n = clamp((value − lower) / (upper − lower), 0, 1)

energy = round(n × confidence × stored_scale, 8)

Missing metrics give energy 0; the information particle remains selectable. Status is never used to invent a successful measurement. Failed results are red, skipped/cancelled results grey, verified benchmarks gold, other successful results green, and informational records blue.

| Metric | Unit | Normalization interval |
|---|---|---|
| utilization_pct, used_pct | % | 0–100 |
| duration_ms | ms | 0–5000 |
| throughput_gflops | GFLOP/s | 0–500 |
| logical_processors | count | 0–32 |
| total_bytes | bytes | 0–128 GiB |
| memory_mib | MiB | 0–16384 |
| file_count | count | 0–2000 |
| characters | count | 0–10000 |

Priority follows the table order (utilization before used_pct). Intervals are display policy, not performance targets. Capacity and duration scores are labeled as such; they do not imply utilization or better performance.

Let v = event energy × operator intensity. Base particle radius = 3 + 5.5v, and angular speed = 0.42v radians/second. Perspective scaling affects apparent radius. Stable SHA-256 event seeds determine initial angle and bounded radial offset. Replay reconstructs event selection and score; camera time is artistic and does not claim deterministic pixel-identical historical physics.

Controls: left drag rotates; right drag pans; mouse wheel or +/− zooms; arrows rotate; Home resets camera; Space pauses/resumes motion; clicking selects evidence. Replay uses original sorted timestamps/IDs and advances one event every 400 ms, explicitly compressing time.

Default 256 particles/30 FPS. Bounds: 32–512 and 15/30/60 FPS. Rendering reduces detail after sustained frame work above 85% of its interval. Benchmark display drops to 15 FPS. This software painter has no GPU instancing; a future renderer can use the same event contract.

Modes are visibly exclusive: DEMO: SYNTHETIC DATA, REAL DATA: OBSERVED, REPLAY: RECORDED EVENTS. Live mode includes retained observed records; the source timestamp shows their age.
