# Engine evaluation

Evaluation combines official capabilities with observed local availability. Costs below are engineering judgments, not measured comparisons between engines.

| Engine | Capability / Windows / offline | Complexity and resource tradeoff | Decision |
|---|---|---|---|
| Qt/PySide6 painter | Native widgets, tables and custom drawing; local runtime already works | One application runtime; CPU rendering leaves GPU compute capacity; limited 3D scale | Selected for alpha |
| Godot | Full game scene graph and Windows exports; editor installed locally | Better rich 3D, but separate Python/SQLite bridge and export lifecycle | Candidate for later renderer |
| Three.js | Browser 3D and instanced objects; offline assets possible | Needs desktop shell and Python bridge for this application | Deferred |
| Babylon.js | Full web graphics engine with particle tools | Web runtime/shell adds integration surface | Deferred |
| Bevy | Rust engine and ECS, native builds | Additional compiled application/runtime bridge and learning surface | Deferred |
| WPF/.NET + Microsoft.Data.Sqlite | Native Windows UI; local .NET exists | Strong native option, but extra interop to existing Python AI tools | Not selected |
| SQLite | Embedded transaction store, no service | Fits immutable event history and bounded queries | Selected |
| DuckDB | Embedded analytical engine | Useful for larger columnar analysis; extra dependency before need | Deferred |
| PyTorch | Existing CUDA runtime verified with numerical output | Reuse as isolated external worker; no multi-GB bundle | Selected for optional GPU |
| TensorRT / ONNX Runtime | Specialized inference paths | Model, runtime and compatibility requirements exceed the initial matrix slice | Discovery only |
| NVML / nvidia-smi | NVIDIA measurements; installed tooling executes | Fixed read-only CLI avoids another binding dependency | nvidia-smi selected initially |
| llama.cpp / Ollama | Local model service interfaces | Model presence and service readiness must be proven separately | Configurable endpoint, no auto-start |

Official references: [Qt deployment](https://doc.qt.io/qtforpython-6.8/deployment/index.html), [PySide6 on PyPI](https://pypi.org/project/PySide6/), [Godot Windows export](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_windows.html), [Three.js](https://threejs.org/docs/), [Babylon.js](https://www.babylonjs.com/), [Bevy](https://bevy.org/learn/quick-start/getting-started/), [Microsoft.Data.Sqlite on NuGet](https://www.nuget.org/packages/Microsoft.Data.Sqlite), [SQLite](https://www.sqlite.org/whentouse.html), [DuckDB](https://duckdb.org/why_duckdb), [PyTorch CUDA synchronization](https://docs.pytorch.org/docs/stable/notes/cuda.html), [NVML](https://docs.nvidia.com/deploy/nvml-api/latest/index.html), [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server).

SourceForge's Godot page was also inspected as an ecosystem discovery source; it identifies itself as an unaffiliated mirror. Official upstream documentation informed selection, and no mirror binary was downloaded. [Mirror listing](https://sourceforge.net/projects/godot-engine.mirror/).
