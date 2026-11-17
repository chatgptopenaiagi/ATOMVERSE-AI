# Run and build

## Mission 002A distribution builds

The current version is 0.2.0-alpha.2. [Installation and platform matrix](../INSTALLATION.md) describes the standalone EXE, Python wheel and Android APK. Existing 0.2.0-alpha.1 assets are immutable.

```powershell
.\scripts\build-standalone.ps1 -BuildPython '<existing-python-with-PyInstaller>'
python -m build --wheel --outdir dist/multiplatform/0.2.0-alpha.2
```

The EXE includes Python/Qt and no CUDA or model weights. The wheel declares PySide6 and psutil, and installs `atomverse-ai` / `python -m atomverse`. Worker entry points resolve inside the installed package. A clean environment is required for wheel acceptance. [Android build and instrumentation instructions](android/README.md) use the same core via Chaquopy, with project-local Gradle dependencies and private signing material. License texts can be extracted with `--export-licenses NEW_DIRECTORY`.

## Portable Windows application

Open dist/ATOMVERSE-AI/ATOMVERSE-AI.exe after building. Keep the entire directory together. The app starts in a labeled demo when no observed history exists. No command-line knowledge is needed for import, sampling, benchmarking, replay or export.

1. Click **Import ARX / JSON** and select an ARX 0.1 machine report.
2. Select a particle to inspect its exact event, units and provenance.
3. Click **Sample hardware**, or explicitly enable continuous telemetry.
4. Open **Benchmark Arena** for a bounded CPU test. For GPU work, choose your existing PyTorch Python executable in Settings.
5. Open **Knowledge Memory** to replay events and **Data Tables** to search/sort measurements.
6. Use **Export view** for JSON or CSV. Exports follow the mode and replay position; table search only filters table rows.
7. Optional AI Intelligence connects to a separately running loopback chat-compatible model. It never starts or downloads a model.

## Source environment

Reuse a working Python 3.14 or 3.15 installation. For a fresh isolated environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe SOFTWARE/main.py
.\.venv\Scripts\python.exe -m pytest -q
```

On the mission workstation, an isolated venv reads existing base-environment Qt/psutil packages via --system-site-packages. Existing PyInstaller is invoked read-only; no global packages were installed or replaced.

## Build

```powershell
.\scripts\build.ps1 -BuildPython '<existing-python-with-PyInstaller>'
```

The build uses project source, places work under build/ and .local/, and outputs dist/candidates/VERSION/ATOMVERSE-AI/. It preserves previous releases. After acceptance the complete folder is copied to dist/releases/VERSION/ATOMVERSE-AI/. GPU libraries and model weights are not bundled.

## Actual executable verification

Use a fresh data directory and a real ARX report:

```powershell
.\dist\ATOMVERSE-AI\ATOMVERSE-AI.exe --data-dir .local/verify-data --gpu-python '<existing-CUDA-PyTorch-python>' --import-arx '<selected-ARX-report.json>' --verify .local/verification
```

The driver interacts with the actual UI, validates event values, runs CPU and GPU tests, checks replay and exports, writes screenshots/report, then closes. It requires a working GPU environment to pass the GPU acceptance check. Independent external readback of SQLite/export and process exit complements this driver.

Advanced launch: --data-dir isolates memory; --import-arx imports an explicitly selected report; --gpu-python selects an existing interpreter. No source path is executed as code.

## Mission 002 executable acceptance

```powershell
.\.venv\Scripts\python.exe scripts/verify_mission002_artifact.py --exe 'dist/releases/0.2.0-alpha.1/ATOMVERSE-AI/ATOMVERSE-AI.exe' --data '.local/mission002/final-data' --output '.local/mission002/final-gui' --arx '<selected-real-ARX-report.json>' --gpu-python '<existing-CUDA-PyTorch-python>'
```

This runs an external watchdog, actual GUI interaction, 15-second idle and controlled-load phases, CPU/GPU numerical benchmarks, process relationships, export/SQLite readback and owned-worker shutdown. The workload starts three bounded 12-second CPU helpers only during explicit verification. Use a copy of a v1 database to verify migration and immutable-body preservation. `--verify` retains the Mission 001 compatibility harness; `--verify-mission002` tests the new interface.

Optional `--verify-ai OUTPUT --ai-endpoint http://127.0.0.1:PORT` tests the actual GUI/AI-worker/persistence path against a separately running local model. It has a 105-second harness deadline and the normal 90-second inference deadline. It does not download or start a model.
