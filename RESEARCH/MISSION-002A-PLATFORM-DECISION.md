# Mission 002A platform decision

The existing application is Python/PySide6 with a standard-library computational core. Flutter was installed, but a Flutter rewrite would create a second event validator and scientific model or require another Python bridge. Native Java Android UI plus Chaquopy directly reuses the current core, has a small dependency surface and uses the already installed SDK/JDK/Gradle. Android renders through Canvas; Windows retains QPainter. No NDK compilation or model download is required.

The shared files are `core.py`, `science.py`, `storage.py` and package version metadata. Android's new `mobile.py` supplies only the platform adapter and bridge. The canonical schema remains `ATOMVERSE-EVENT-SCHEMA.json`; exports remain `atomverse-export/1`, accepting event schemas 1.0/1.1 and preserving scientific categories. SQLite remains version 2. Immutable event bodies are compared during cross-platform roundtrip acceptance.

Android SDK calls expose device RAM, app CPU time, app PSS and app-data volume capacity. These have different scope from Windows counters. GPU workload, per-process GPU attribution, device-wide CPU percentages and temperature are not inferred from rendering or CPU counts. Missing sensors are explicitly unavailable. No observation service or background monitoring is installed.

Windows one-file packaging uses the existing PyInstaller 6.22.3 installation. The runtime is self-contained and extracts to a temporary folder; optional model/GPU environments remain external. The Python wheel is pure project Python with declared native dependencies, supported on Windows 11 x64 / Python 3.14–3.15 for the GUI. It makes no universal desktop compatibility claim.

The installed API 37 Google Play emulator image advertises `x86_64,arm64-v8a` and `libndk_translation.so`. This permits testing the **same ARM64 APK** through native translation, subject to actual launch verification. It is not physical ARM64-device coverage, nor evidence that every Android API level or vendor driver works. No device was attached at discovery.

Android is new application functionality. The release therefore advances from 0.2.0-alpha.1 to **0.2.0-alpha.2**, following the owner's explicit versioning condition. Original assets are not replaced. All three new distributions share the incremented version and one prerelease.

Primary references inspected during this mission:

- [Chaquopy Android integration and supported build configuration](https://chaquo.com/chaquopy/doc/current/android.html)
- [Chaquopy runtime/version compatibility](https://chaquo.com/chaquopy/doc/current/versions.html)
- [Chaquopy Java API](https://chaquo.com/chaquopy/doc/current/java.html)
- [Android Gradle plugin 9.1 compatibility](https://developer.android.com/build/releases/agp-9-1-0-release-notes)
- [Android explicit document access](https://developer.android.com/training/data-storage/shared/documents-files)
- [Android MemoryInfo source semantics](https://developer.android.com/reference/android/app/ActivityManager.MemoryInfo)
- [PyInstaller subprocess and one-file behavior](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html)

Measured build/runtime outcomes, rather than these proposals, determine the final acceptance report.

Real wheel acceptance found an Anaconda/PyPI DLL collision: PyPI Qt 6.11 imports unversioned Windows ICU symbols, while the inherited Anaconda DLL search directory supplied a different `icuuc.dll` with versioned symbols. PE import/export inspection confirmed the mismatch. The installed entry point now loads Windows' system ICU by absolute path only for the PyPI Qt layout; frozen and Conda Qt layouts retain their matched runtimes. This is process-local and does not modify PATH, system DLLs or existing environments.

Android first launch also exposed Activity recreation during first database migration. `mobile.py` serializes construction across overlapping Activity workers, and the ready flag is set only after the first validated packet is available. History display is bounded to 256 events and document export streams rows into a temporary private file to bound Java heap use. Failed acceptance attempts are retained alongside subsequent results.
