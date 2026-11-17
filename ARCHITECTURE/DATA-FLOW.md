# Data flow

1. Operator selects a source or bounded benchmark.
2. Intake limits size and checks source format/version.
3. Adapter translates known fields and units; unknown values remain unknown.
4. Schema validation rejects malformed or non-finite data.
5. Calculation engine produces deterministic dimensionless scores.
6. Database commits event, configuration and evidence references.
7. Bounded visualization state consumes the event and exposes selection.
8. Tables, replay and exports use stored values.
9. Optional AI receives explicitly chosen evidence and returns labeled interpretation.

Synthetic events carry an explicit marker throughout this path. Mode changes replace the displayed data set. Raw reports stay local unless explicitly reviewed for publication.
