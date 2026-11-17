# Visualization model proposal

The implemented alpha is described in [ATOMVERSE-VISUALIZATION-SPEC.md](../ATOMVERSE-VISUALIZATION-SPEC.md). This page preserves the broader design intent; white knowledge nodes and richer simulations remain future extensions.

A central workstation nucleus is surrounded by CPU, GPU, memory, storage, AI, code, database and Guardian orbits. Events produce selectable objects with stable IDs and deterministic orbital targets. Colors distinguish errors, successful execution, benchmarks, inputs and knowledge.

Normalize using documented metric ranges; clamp finite inputs; multiply workload intensity by confidence and display scale. Keep artistic idle motion separate from measured workload. Operators control intensity, zoom, pan, rotation, selection, pause, frame cap and particle limit.

Live and replay modes show clear timestamps and source labels. Demo mode is marked DEMO: SYNTHETIC DATA. Replay uses recorded order/timestamps and never writes duplicate benchmark observations.
