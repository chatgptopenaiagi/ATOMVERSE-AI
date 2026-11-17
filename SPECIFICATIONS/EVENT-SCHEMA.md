# Event schema proposal

**Implemented contract:** [ATOMVERSE-EVENT-SCHEMA.json](../ATOMVERSE-EVENT-SCHEMA.json) and core.validate_event. The notes below preserve the genesis design intent; the JSON Schema plus documented runtime constraints is authoritative for alpha imports.

Version 1.0 events require event_id, timestamp_utc, source, category, component/device, status, data_kind and metrics. Each metric has a finite numeric value and explicit unit. Provenance identifies an explicit source or benchmark configuration.

Allowed data kinds distinguish observed, synthetic and interpretation records. Calculated normalization inputs and simulated visual output are separate fields. Status distinguishes PASS, FAIL, INFO, SKIP and CANCELLED. Unsupported schema versions fail gracefully.

The mission's sample GPU event is illustrative only. Real results are separately recorded in EVIDENCE/ATOMVERSE-BENCHMARK-RESULTS.json. The alpha schema and validator enforce structured value/unit metrics, canonical UTC, finite values, known statuses, size bounds and deterministic visual calculations.
