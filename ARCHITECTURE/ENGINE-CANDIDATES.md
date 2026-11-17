# Engine candidates

**Selected after discovery:** Python/Qt for the native alpha, SQLite for memory and external PyTorch for optional CUDA benchmarking. Godot, Three.js, Babylon.js, Bevy and native .NET were evaluated for Windows support, resource use, dependencies, offline operation, maintenance and packaging. See the [engine evaluation](../RESEARCH/ENGINE-EVALUATION.md).

Evaluate SQLite first, DuckDB for future analytics, and existing SQL Server only where useful. Compare existing Python/PyTorch, ONNX Runtime, TensorRT and llama.cpp interfaces. Prefer already working environments and stable report/CLI boundaries over copied internals.

Research must cite official documentation and record inspected versions and local evidence.
