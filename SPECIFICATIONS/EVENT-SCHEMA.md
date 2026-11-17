# Event schema proposal

Version 1.0 events require event_id, timestamp_utc, source, category, component/device, status, data_kind and metrics. Each metric has a finite numeric value and explicit unit. Provenance identifies an explicit source or benchmark configuration.

Allowed data kinds distinguish observed, synthetic and interpretation records. Calculated normalization inputs and simulated visual output are separate fields. Status distinguishes PASS, FAIL, INFO, SKIP and CANCELLED. Unsupported schema versions fail gracefully.

The mission's sample GPU event is illustrative only. No numeric example is a real measurement. A machine-readable schema and validator are Stage 2 deliverables.
