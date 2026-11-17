# Mission 002A — Multiplatform Expansion

**Version: 0.2.0-alpha.2. Mission status: SUCCESS.** All five public release assets were downloaded and matched the locally verified SHA-256 digests. [Open the prerelease](https://github.com/chatgptopenaiagi/ATOMVERSE-AI/releases/tag/v0.2.0-alpha.2). Publication readback is recorded in [final verification](EVIDENCE/MISSION-002A-FINAL-VERIFICATION.json). This is an experimental prerelease, not a finished intelligence platform.

Android adds application functionality, so this mission uses the explicitly authorized version increment. The original v0.2.0-alpha.1 ZIP, executable, checksum asset, tag and evidence remain intact. Its portable ZIP SHA-256 is `4db1f2cec468e4adef3252ff71b9cba0ad5caa9a2ddf49c4d7d33c0a026767d2`. Mission 002 documents are archived in RELEASES/0.2.0-alpha.1; the original human vision is unchanged.

| Package | Bytes | SHA-256 |
|---|---:|---|
| `ATOMVERSE-AI-0.2.0-alpha.2-windows-x64.exe` | 50,786,764 | `abed85bb309f3486c9e424d6ac603a5cedec14c0c53b408495b60afe2bce97c3` |
| `atomverse_ai-0.2.0a2-py3-none-any.whl` | 106,578 | `2a8b1411def9fa57d021215520f62df1aa6f43ce7d6820f2e098471bb898586c` |
| `ATOMVERSE-AI-0.2.0-alpha.2-android-arm64.apk` | 22,533,756 | `5b3f29266d2f4134c6037dbf86a7f559b401ec87af8f86ae625e0cd838075b12` |

Windows EXE acceptance ran the actual promoted one-file executable from a working directory outside the source tree. It verified native GUI interaction, live CPU/RAM/NVIDIA/process observations, real ARX import, CPU and CUDA benchmarks, SQLite integrity, replay, JSON readback, optional-AI unavailable handling and clean worker shutdown. Python/model/CUDA toolkits are not required or silently bundled beyond the included desktop Python runtime. The EXE is not Authenticode signed.

The wheel installed in a fresh environment without system site packages. Metadata, pure-Python tags, import, console/module entry points, license export, real GUI observation and benchmarks, SQLite/export readback, Android-history import and uninstallation passed. The tested Python was Anaconda 3.14.9 on Windows 11 x64. Python 3.15 is allowed by metadata but did not receive a separate wheel GUI run. The `py3-none-any` tag describes package contents, not universal desktop support.

The release-signed ARM64 APK passed 20 actual runtime checks and package/signature checks on an API 37 x86_64 emulator using Android's `libndk_translation` ARM64 bridge. The same ARM64 APK intended for publication was installed, launched and operated; no x86 application binary substituted for it. Rotation, pinch zoom, live Android RAM/app CPU, unavailable GPU states, SQLite, document export, history import/replay, malformed-input rejection and clean worker shutdown passed. The normal system picker also exported and reimported a validated 159-event history. No physical ARM64 device was attached. Other Android API levels and vendor devices remain untested.

All **85 Python tests** pass, retaining all **79 original tests**. Cross-platform verification preserved nine desktop events byte-semantically on Android and 149 Android events through desktop and installed-wheel SQLite/export. OBSERVED, DERIVED, AI_INTERPRETED, SIMULATED and UNAVAILABLE classifications survived the exchange. The original core, science, storage algorithms and published JSON contract remain unchanged; platform adaptation lives in `mobile.py`.

Measured Windows overhead, sampling delay and GUI latency are in [performance evidence](EVIDENCE/MISSION-002A-PERFORMANCE.json). Android's recorded final-frame paint time is a single sample, not a physical-device performance benchmark. Initial failures and fixes—including concurrent migration, a PyPI Qt/Conda ICU collision and concurrent-build latency—are preserved in [resolved issues](EVIDENCE/MISSION-002A-RESOLVED-ISSUES.json).

Android exposes app CPU, device RAM, app PSS and storage capacity. It does not claim Windows process relationships, NVIDIA CUDA, device-wide CPU utilization, GPU workload sensors or an embedded Qwen model. Its normal operation is offline; AI-interpreted history remains readable. Rendering and history views are bounded to 256 objects/events, and exports stream rows. Physical-device coverage, additional Android versions, mobile CSV export and optional authorized AI endpoints are next priorities.

See [installation and platform matrix](INSTALLATION.md), [architecture](ATOMVERSE-ARCHITECTURE.md), [Android build instructions](SOFTWARE/android/README.md), and [source/build instructions](SOFTWARE/README.md). Verified packages are promoted under `dist/releases/0.2.0-alpha.2`; future candidate builds use a separate directory. No old release asset is overwritten.
