# Engineering decisions

## ADR-000 — documentation precedes implementation

Accepted by the mission contract. Stage 1 must be remotely verified before environment discovery and implementation. The first commit contains documentation only.

## ADR-001 — evidence before stack selection

Pending discovery. Compare existing runtimes and official engine capabilities; record chosen stack, rejected alternatives, tradeoffs, dependency licenses and observed hardware.

**Resolved after Stage 1:** Python 3.14, existing PySide6 6.11, SQLite and psutil are selected for the alpha. Qt supplies native controls and a projected universe with low integration overhead; the existing CUDA/PyTorch environment stays external. Godot, web graphics engines and Bevy remain candidate renderers. This choice optimizes the first inspectable, packaged information flow, not maximum visual scale. See [evaluation](../RESEARCH/ENGINE-EVALUATION.md) and [implementation](../ATOMVERSE-ARCHITECTURE.md).

## ADR-002 — epistemic boundaries

Accepted. Observed values, calculated scores, AI interpretations and simulated properties are separate. Unknown values are not measured zeros. Demo records are labeled and isolated from real data.

## ADR-003 — immutable bounded memory

SQLite event IDs are immutable and imports are idempotent. Conflicting IDs or capacity exhaustion fail visibly; nothing silently replaces or prunes history. Atomic exports provide a recovery path. See [database contract](../ATOMVERSE-DATABASE-SCHEMA.md).

## ADR-004 — external AI compute

GPU benchmarks run a fixed worker script in an operator-selected existing Python interpreter. The GUI never loads PyTorch. One subprocess, a 30-second wall limit, small tensor bounds and explicit cancellation reduce contention. CPU work remains independently usable without PyTorch. Existing TensorRT was imported successfully but inference is not implemented.

## ADR-005 — ARX schema boundary

Support the actual ARX machine envelope 0.1 and nested GPU schema 1.0. Reject Project DNA 0.2 rather than guessing. Read only allowlisted values; omit machine identifiers, paths and unreliable CIM AdapterRAM. Prefer NVIDIA tooling's explicit dedicated_vram_bytes for capacity. Preserve report hashes and JSON pointers.

## ADR-006 — local model readiness

Historical Qwen3-Coder model paths are unavailable; a different Ollama qwen3.8:27b manifest/blob is present. No model was started. Provide a configurable loopback chat endpoint and honest errors. Protocol tests use a labeled test server and do not prove real model inference.
