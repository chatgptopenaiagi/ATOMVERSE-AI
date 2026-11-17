# Install ATOMVERSE AI

Mission 002A adds a native Android client and installed Python entry point. These are material changes, so the software family advances to **0.2.0-alpha.2**. The original **0.2.0-alpha.1** portable ZIP, checksum manifest, release tag and evidence remain unchanged.

## Windows standalone EXE

Download `ATOMVERSE-AI-0.2.0-alpha.2-windows-x64.exe` from the [multiplatform prerelease](https://github.com/chatgptopenaiagi/ATOMVERSE-AI/releases/tag/v0.2.0-alpha.2). Check its SHA-256 against the accompanying manifest and open it. Python and the native Qt interface are included. The executable extracts its runtime into a temporary directory at startup; first launch takes longer than the portable folder build. No administrator privileges are required. The executable is not Authenticode signed.

Observation is off at startup. Click **Start live observer** to enable CPU/RAM/disk/process sampling and supported NVIDIA measurements. Data defaults to `%LOCALAPPDATA%\ATOMVERSE-AI`; `--data-dir PATH` selects a different history. Existing history uses the same additive SQLite v2 schema. Export JSON/CSV before sharing or changing machines.

CUDA benchmarking requires an independently installed compatible NVIDIA driver and PyTorch Python, selected through Settings or `--gpu-python`. Local Qwen interpretation requires the operator's separately running loopback endpoint/model. Neither is required for normal use; neither is included in the executable. Use `--export-licenses NEW_DIRECTORY` to extract third-party license texts without starting the interface.

The previous verified folder installation remains available as [0.2.0-alpha.1 portable ZIP](https://github.com/chatgptopenaiagi/ATOMVERSE-AI/releases/tag/v0.2.0-alpha.1). Keep that complete folder together.

## Python wheel

The supported desktop environment is **Windows 11 x64, Python 3.14 or 3.15**. In PowerShell:

```powershell
python -m venv atomverse-env
.\atomverse-env\Scripts\python.exe -m pip install .\atomverse_ai-0.2.0a2-py3-none-any.whl
.\atomverse-env\Scripts\atomverse-ai.exe --version
.\atomverse-env\Scripts\atomverse-ai.exe
```

The wheel contains pure Python project code. `py3-none-any` describes that payload, **not universal desktop support**. Installation resolves the declared native PySide6 6.11.0 and psutil 7.2.2 dependencies. The desktop entry point explicitly requires Windows. `python -m atomverse` is equivalent. Core modules (`atomverse.core`, `science`, `storage`) use the standard library and are shared with Android. Other desktop operating systems have not been verified.

Uninstall with `python -m pip uninstall atomverse-ai` inside the environment. Uninstallation deliberately preserves the user's history directory. The wheel is a Python distribution, not a standalone executable.

## Android ARM64 APK

Download `ATOMVERSE-AI-0.2.0-alpha.2-android-arm64.apk`. It targets ARM64 (`arm64-v8a`), Android API 24 or later. Use Android's normal installer and allow that installer to install the selected APK when prompted. The APK is signed with the project's release signing key; it is not a Play Store distribution. Signature verification and emulator execution are documented in the Mission 002A evidence. No physical ARM64 device was available in this mission.

The first screen is **DEMO: SYNTHETIC DATA**. Drag to rotate and tilt, pinch to zoom, use a two-finger drag to pan, and tap a particle or **Data** to inspect its event. **Start live** enables foreground observation; **Pause live** stops collection. Leaving the application stops observation. **Replay** shows recorded history and a seek slider. **Import** and **Export** use Android's system document picker and versioned `atomverse-export/1` JSON. Imports accept at most 4 MiB / 1,000 events at a time; exports contain at most the 10,000 retained rows. Imported evidence is protected, while live samples follow configurable age/row retention. If protected history fills the cap, export it and select a fresh installation/history rather than silently deleting evidence.

Android measures device RAM, app proportional set size, app CPU time and the app-data storage volume. CPU percentage is derived from **this app's** CPU time and normalized by reported logical processors. It does not measure every process or device-wide CPU load. GPU workload, VRAM and GPU temperature are explicitly unavailable. The desktop's Windows process APIs, NVIDIA monitoring, CUDA benchmarks and local Qwen interface are not included on Android. Android remains fully usable offline without a model and does not request network, broad file-access, microphone or location permissions.

## Platform compatibility

| Capability | Windows EXE | Python wheel on Windows | Android ARM64 |
|---|---|---|---|
| Shared validation, scientific classifications, visual-energy formula | Yes | Yes | Same Python source |
| Interactive universe, demo, inspection, history, replay | Yes | Yes | Native touch interface |
| SQLite v2 and schema 1.0 / 1.1 JSON exchange | Yes | Yes | Yes, bounded imports |
| CSV export | Yes | Yes | JSON export; convert with desktop/core |
| Device CPU / per-core / Windows processes | Yes | Yes | App CPU only; no process inventory |
| RAM and storage | Device RAM / disk I/O | Same | Device RAM / app PSS / storage capacity |
| NVIDIA telemetry / CUDA benchmark | Optional installed support | Optional installed support | Unavailable |
| CPU benchmark / ARX adapter | Yes | Yes | Import normalized history only |
| Local Qwen interpretation | Optional loopback endpoint | Same | Read imported AI interpretations |
| Bundled Python runtime | Yes | No; installed environment | Yes, Chaquopy ARM64 |

Every event keeps its original observation, calculation, AI, simulation or unavailable classification. A visual score is dimensionless and is never a physical energy measurement.
