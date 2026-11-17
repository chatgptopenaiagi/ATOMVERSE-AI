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
| Chaquopy 17.2.0 | Android Python bridge and packaged ARM64 runtime | MIT; LICENSES/CHAQUOPY.txt, https://github.com/chaquo/chaquopy/blob/17.2.0/LICENSE.txt |
| ARX 4.0.0b6 | External read-only report producer | MIT; not bundled, https://github.com/chatgptopenaiagi/ARX/blob/main/LICENSE |

The portable build keeps Qt as replaceable shared libraries. Build instructions and application source are in this repository. Reverse engineering for debugging modifications to LGPL components is permitted. Dependency notices and license texts accompany the unsigned experimental prerelease. NVIDIA NVML, CUDA, PyTorch, Ollama and model weights are not bundled; optional integrations use existing installations. The project's own general-purpose license decision remains with the owner.

The standalone Windows executable extracts its dynamic Qt/Python libraries to a temporary directory. Rebuilding with modified dependencies is documented in SOFTWARE/README.md; `--export-licenses NEW_DIRECTORY` makes bundled notices accessible. The Python wheel declares native dependencies separately. Android bundles CPython and Chaquopy, with license texts in APK assets; it does not bundle Qt, psutil, NVIDIA libraries or AI models. Android framework libraries come from the installed operating system.
