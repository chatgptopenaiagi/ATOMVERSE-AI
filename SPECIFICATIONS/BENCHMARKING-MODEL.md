# Benchmarking model proposal

The alpha implements CPU float matrix and optional CUDA/PyTorch float32 matrix workers. [Actual measured results](../EVIDENCE/ATOMVERSE-BENCHMARK-RESULTS.json) and [architecture limits](../ATOMVERSE-ARCHITECTURE.md) supersede the initial estimates below. Other benchmark categories remain future work.

Initial scope: one bounded CPU workload and one GPU workload if a verified runtime is available. Optional later categories: tensor operations, transfers, matrix multiplication, cuDNN convolution, TensorRT inference, allocations, model load and inference latency.

Each result records workload size, iterations, runtime/framework versions, device, warmup, synchronization, elapsed duration, verification output and status. Check results numerically; successful process exit alone is insufficient.

Enforce a hard wall timeout, conservative memory cap and one active benchmark. Provide cancellation. Do not allocate all VRAM. Leave headroom for Windows, rendering and other applications. Unsupported runtimes produce SKIP, failures produce FAIL, cancellation produces CANCELLED. Never animate a failed workload as success.

Benchmark comparisons require matching configuration and relevant environment. A faster unmatched run is not evidence of a performance improvement.
