# Native Android client

Java Android UI and public SDK adapters call `atomverse.mobile` through [Chaquopy 17.2](https://chaquo.com/chaquopy/doc/current/android.html). Gradle copies an explicit allowlist directly from `SOFTWARE/atomverse`; there is no second implementation of event validation, normalization equations, classifications, replay or SQLite memory. Python 3.14, AGP 9.1.0, Gradle 9.3.1 and JDK 21 are used for this build. Android SDK 36 compiles the application; target SDK 36, minimum SDK 24, ARM64 only. No NDK compilation is needed.

From the project root in PowerShell 7:

```powershell
.\scripts\build-android.ps1 -Gradle C:\path\to\gradle.bat -JavaHome C:\path\to\jdk21 -BuildPython .\.venv\Scripts\python.exe -Tests
```

Use existing `ANDROID_HOME` / `ANDROID_SDK_ROOT`. Gradle dependencies and signing material remain under ignored `.local`. The script creates a private signing key only if none exists, preserves it on subsequent builds and never prints its password. Back up `.local/android-signing` securely if maintaining upgrades of this application; a different key cannot update an existing Android installation. Never commit or publish this directory.

Release output is `app/build/outputs/apk/release/app-release.apk`. The instrumentation APK under `app/build/outputs/apk/androidTest/release` is a test harness, not a user release asset. Install both on an explicitly selected test device and run:

```powershell
adb -s DEVICE install -r SOFTWARE/android/app/build/outputs/apk/release/app-release.apk
adb -s DEVICE install -r SOFTWARE/android/app/build/outputs/apk/androidTest/release/app-release-androidTest.apk
adb -s DEVICE shell am instrument -w com.atomverse.ai.test/com.atomverse.ai.AcceptanceRunner
```

Acceptance inspects actual Python startup, touch rotation/pinch, live Android measurements, classifications, SQLite integrity, shared desktop-history import, export, malformed-input recovery, replay and worker shutdown. The runner writes machine-readable evidence under the target application's external-files `verification` directory. A successful Gradle build alone is not runtime verification.

One scheduled executor owns Python and SQLite. Sampling runs only after visible opt-in and only while foregrounded; no service is installed. At most 256 objects render at configurable 10–30 fps. Live samples retain 3,000 rows / 24 hours by default, bounded to 10,000; imported history is protected. File selection uses the [Storage Access Framework](https://developer.android.com/training/data-storage/shared/documents-files). [ActivityManager.MemoryInfo](https://developer.android.com/reference/android/app/ActivityManager.MemoryInfo), app CPU time, PSS and StatFs are the available measurement sources. Unsupported sensors produce `UNAVAILABLE` records. No network permission or AI model is included.
