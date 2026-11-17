# Dependency and reuse matrix

Inspected 2026-11-17. Public repository descriptions are discovery leads; README/source inspection is separately identified. No private repository names or raw credentials are published.

| Candidate | Observed interface/capability | Decision and boundary |
|---|---|---|
| ARX 4.0.0b6 | Installed desktop plus public MIT source; CLI -o output deep produces schema 0.1; gpu_compute schema 1.0 | Consume explicit JSON. Fresh scan ran from an isolated source checkout. Installed ARX untouched. |
| COG | Local WPF/Core source docs; typed diagnostics, sanitized JSON export, job-based process boundaries | Architectural reference. No direct parser or session monitoring added. Never access vault/auth stores. |
| DRAGONHYDRA | Local module contracts, SQLite records, explicit job APIs and optional local-model interface | Reuse interface lessons only. Sports-domain server dependencies are unnecessary here. |
| Existing PyTorch | Actual import, CUDA device detection, synchronized matrix execution | External selected interpreter; do not copy or reinstall environment. |
| Existing TensorRT | Python package import returns 11.4.0.106 in a separate environment | Detected only. Inference integration deferred; import is not inference verification. |
| Qwen3-Coder historical installation | Previously reported D:/E: LocalAI locations absent now | No available exact model claimed. Configurable loopback endpoint provided. |
| Ollama qwen3.8:27b | Manifest and referenced local blobs present, model layer 16,810,714,464 bytes | Different model. No serving process observed and no model loaded. |
| CHESS-BOOK-ARENA tooling | Existing PySide6, pytest and PyInstaller installations execute | Read-only build tooling reuse. No chess source or dependencies copied. |
| Free-Bible-Reader | Existing independent desktop/database app and dependency-license texts | Packaging reference only; no application coupling. |
| agent-process-microscope | Public README documents explicit selected Codex JSON intake, normalized events and replay | Potential future adapter. No passive attachment or code reuse implemented. |
| huggingface-helper-scanner | Public README describes bounded public model metadata CLI | Future metadata source. Not a verified local hardware/model engine. |
| GENESIS-RELAY | Public README describes continuation capsules and explicit reconstruction workflow | Future project packaging reference; not a visualization or benchmark dependency. |

Remote sources: [ARX](https://github.com/chatgptopenaiagi/ARX), [COG](https://github.com/chatgptopenaiagi/COG), [DRAGONHYDRA](https://github.com/chatgptopenaiagi/DRAGONHYDRA), [APM](https://github.com/chatgptopenaiagi/agent-process-microscope), [HHS](https://github.com/chatgptopenaiagi/huggingface-helper-scanner), [GENESIS RELAY](https://github.com/chatgptopenaiagi/GENESIS-RELAY).
