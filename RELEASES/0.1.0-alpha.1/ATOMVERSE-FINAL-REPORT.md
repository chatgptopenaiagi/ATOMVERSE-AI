# ATOMVERSE AI Mission 001 — final engineering report

**Version 0.1.0-alpha.1. Experimental Windows vertical slice verified on 2026-11-17.**

## Stage 1: completed first

The public repository is [chatgptopenaiagi/ATOMVERSE-AI](https://github.com/chatgptopenaiagi/ATOMVERSE-AI). Its documentation-only genesis commit is 64f3a79938fe52778e207fb6bfa9aba33778662e. GitHub readback verified the default branch, public visibility, README, original human vision and roadmap before application development began. The original twelve concepts and the distinction between physical analogy, proposals, implementation and experiments remain preserved.

## Stage 2: measured outcome

The portable Windows executable launches a native interface. Real ARX evidence becomes validated events, selectable visual objects, precise inspectable measurements and persistent SQLite history. A new application can also run offline with visibly synthetic demonstration data.

The packaged acceptance run imported **38 real ARX events**, ran CPU and GPU matrix tests, recorded an intentional malformed-input failure, sampled three hardware events, and retained **44 observed records**. External verification reopened SQLite, checked integrity, compared the JSON export to every stored event, validated all events, and confirmed process exit code 0 with **zero surviving child processes**.

**46 automated tests passed, with no failures, errors or skips.** Coverage includes schema and units, finite values, normalization, deterministic energy, ARX contract checks, immutable transactions, retention bounds, replay, exports, source permissions, environment discovery, local-model transport boundaries, worker output verification, cancellation, deadlines, failed executables, GUI controls and shutdown. [Functional evidence](EVIDENCE/ATOMVERSE-FUNCTIONAL-TESTS.json), [actual binary evidence](EVIDENCE/ATOMVERSE-GUI-VERIFICATION.json).

## Actual benchmark samples

| Backend | Workload | Iterations | Measured duration | Result |
|---|---|---:|---:|---|
| CPU / Python float matrix | 16 × 16 | 440 | 300.275 ms | PASS; checksum 12160 |
| RTX 3050 / PyTorch CUDA float32 | 256 × 256 | 3960 | 300.087 ms | PASS; checksum 65536 |

GPU peak PyTorch allocation was 9.125 MiB. This excludes driver/context and other applications' allocations. CUDA work synchronized every iteration. These small, different workloads are acceptance checks; they are not a CPU/GPU speedup comparison, peak-device benchmark or evidence of regression/improvement. Raw configuration and timings are in [benchmark results](EVIDENCE/ATOMVERSE-BENCHMARK-RESULTS.json).

The universe painted **53 frames while the GPU worker ran**. During the full interaction/stress verification, 155 paints averaged 21.490 ms with a maximum of 59.815 ms. The 512-particle stress case automatically reduced rendered detail to 216. These are paint timings, not a sustained FPS guarantee. Software painting remains a scale limitation.

## Workstation and reuse

Fresh checks found Ryzen 5 5600G (6 cores / 12 threads), approximately 64 GiB RAM, RTX 3050 with 6 GiB dedicated VRAM, compute capability 8.6, NVIDIA driver 621.24, Windows 11 Insider build 29695, Vulkan 1.4.357 and DirectX 12. Existing PyTorch 2.15.0+cu134 exercised CUDA 13.4; cuDNN 92600 was available. TensorRT 11.4.0.106 imported in a separate environment; no TensorRT inference was tested.

Existing Qt/Python/PyInstaller tools were reused. ARX produced a fresh report from an isolated source checkout; its installed application was not modified. COG and DRAGONHYDRA informed boundaries through read-only source/document inspection. Additional public repositories were reviewed for later adapters. The [reuse matrix](RESEARCH/DEPENDENCY-REUSE-MATRIX.md) distinguishes inspected capability from implemented integration.

Six selected pre-existing executable/manifest/document files retained their original SHA-256 hashes. This supports preservation of those files, not a whole-disk proof. No existing installation, credential store or sibling source repository was intentionally modified. [Preservation evidence](EVIDENCE/PRESERVATION-VERIFICATION.json).

## Build and use

Local executable: dist/ATOMVERSE-AI/ATOMVERSE-AI.exe. Keep the complete folder together. Build/source instructions: [SOFTWARE/README.md](SOFTWARE/README.md). Default local history: %LOCALAPPDATA%/ATOMVERSE-AI/. Exact executable hash and source files: [BUILD-MANIFEST](EVIDENCE/BUILD-MANIFEST.json).

The artifact is an unsigned portable development build. It is not a public GitHub binary release. Project licensing remains the owner's decision; dependency notices and license texts are included separately.

## Known limitations and unresolved work

- Rendering is a rotatable 3D projection painted by Qt, not a full game engine or physical simulation. Larger scenes need a more efficient renderer.
- Qwen3-Coder's historical file locations are unavailable. A different qwen3.8:27b manifest and model blob exist, but no server was running and no real-model inference was performed. The configurable endpoint and protocol are implemented; actual model integration remains unverified.
- CPU/GPU matrices are the only implemented benchmark categories. cuDNN convolution, TensorRT inference, transfers, allocations, model loading and inference latency remain future work.
- Hardware/software maps are inspectable record summaries. Source Code Galaxy reads bounded file metadata; it does not yet build a dependency graph. Direct COG/Codex result adapters and broader service/process/event-log observation are deferred.
- Automated comparable-session regression detection, benchmark comparison UI and long-term knowledge summaries are not implemented. Original measurement records remain available for later analysis.
- Replay preserves event order and timestamps but compresses playback to one event per 400 ms. It does not reconstruct historical physical motion.
- History stops at its documented capacity; there is no automatic archival UI. Export and a new data directory are the current retention workflow.
- GUI verification used this Windows Insider workstation. Other Windows builds, accessibility/high-DPI configurations, installers and digital signing have not been validated. No comprehensive security or performance certification is claimed.

## Next priorities

1. Improve renderer efficiency and evidence-panel usability with measured frame budgets.
2. Add comparable benchmark sessions, controlled warmup/sampling and additional bounded workloads.
3. Verify an operator-selected running local model and add evidence-citation checks.
4. Add versioned COG/Codex adapters, richer source relationships and explicit archival controls.

The first verified information flow is complete: **REAL DATA → EVENT → VISUAL OBJECT → MEASUREMENT → MEMORY**. The broader human vision remains the continuing product objective.
