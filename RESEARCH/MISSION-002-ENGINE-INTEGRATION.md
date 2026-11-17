# Mission 002 engine discovery and reuse

Investigation date: 2026-11-17. Existing applications were inspected read-only. ATOMVERSE remains independently runnable. Names alone were not treated as capability evidence.

| Engine | Inspected evidence | Selected interface | Verification and limits |
|---|---|---|---|
| ARX | Installed executable, source checkout, fresh real machine JSON | Existing envelope 0.1 and GPU compute 1.0 report adapter | Fresh baseline imported 38 events. No ARX modification. |
| COG | `src/COG.Core/Diagnostics.cs`, `DiagnosticHistory.Export`, explicit GUI export | Operator-selected JSON `version: 2.0.0`, timestamp and numeric category/outcome enums | Adapter tested against contract fixtures. No private diagnostic history or vault read. Producer outcomes are not independent reruns. |
| DRAGONHYDRA | `docs/architecture/MODULE-CONTRACTS.md`, `src/dragonhydra/module_registry.py`, definition and snapshot return shape | Explicit exported `schema_version: 1`, `registry_version: module-registry/1` snapshot | Adapter tests states and version rejection. No authenticated API connection or current runtime-readiness claim. |
| Agent Process Microscope | Public repository tree, README, `apm/core/events.py`, observer and schema locations | Research reference; no runtime dependency | Focused PID/workspace attachment differs from system telemetry. No private Codex session ingestion enabled. |
| Existing PyTorch | Fresh import, CUDA availability, cuDNN version, RTX 3050 capability 8.6 | Existing explicitly selected Python subprocess | Retained bounded matrix benchmark; no new CUDA environment. |
| Existing TensorRT | Fresh import of 11.4.0.106 | Deferred optional benchmark backend | Import does not verify inference or a benchmark. |
| Ollama / Qwen | Client 0.40.16, existing qwen3.8:27b manifest and local blobs, isolated loopback test | Optional native Ollama chat or local `/v1/chat/completions` | CPU-only native requests; 90-second application deadline. See AI evidence for actual results. No model downloaded. |

The owner's public repository list was refreshed with authenticated GitHub CLI. Other repositories were not imported simply because they mentioned memory, AI or monitoring. No sibling application is automatically started.

Sources: [COG](https://github.com/chatgptopenaiagi/COG), [DRAGONHYDRA](https://github.com/chatgptopenaiagi/DRAGONHYDRA), [ARX](https://github.com/chatgptopenaiagi/ARX), [Agent Process Microscope](https://github.com/chatgptopenaiagi/agent-process-microscope), [Ollama chat API](https://docs.ollama.com/api/chat), [Windows process snapshot](https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-createtoolhelp32snapshot), [Windows process-entry contract](https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/ns-tlhelp32-processentry32w), [committed-memory contract](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-performance_information), [psutil documentation](https://psutil.readthedocs.io/en/latest/). NVIDIA binding layout was checked against installed CUDA 13.4 `nvml.h`, including its WDDM memory limitation.
