# Third-party components

ATOMVERSE's own source license is undecided; see LICENSE-DECISION.md. Existing installations are reused read-only during development. No sibling application source is copied into the runtime.

| Component | Use | License / upstream |
|---|---|---|
| CPython | Application runtime | Python Software Foundation license, https://docs.python.org/3/license.html |
| Qt / PySide6 / Shiboken6 6.11.0 | Native widgets and painter | LGPLv3/GPLv3/commercial alternatives, https://doc.qt.io/qtforpython-6/licenses.html |
| psutil 7.2.2 | Explicit hardware sampling | BSD-3-Clause, https://github.com/giampaolo/psutil/blob/master/LICENSE |
| SQLite | Local database in Python runtime | Public domain, https://www.sqlite.org/copyright.html |
| PyInstaller 6.22.3 | Development packaging tool/bootloader | GPLv2 with exception permitting bundled applications, https://pyinstaller.org/en/stable/license.html |
| PyTorch | Optional external GPU worker environment | BSD-style; not bundled, https://github.com/pytorch/pytorch/blob/main/LICENSE |
| ARX 4.0.0b6 | External read-only report producer | MIT; not bundled, https://github.com/chatgptopenaiagi/ARX/blob/main/LICENSE |

The portable build keeps Qt as replaceable shared libraries. Build instructions and application source are in this repository. Do not restrict reverse engineering for debugging modifications to LGPL components. Dependency notices and license texts must accompany any distributed binary; the build includes collected license files. The current deliverable is an unsigned local development build, not a published binary release.
