# Knowledge memory proposal

SQLite is preferred initially. Preserve immutable events, timestamps, source identities, units, hardware/software versions, configuration, outcome, evidence references and derived simulation inputs.

Use indexed timestamps and categories, stable event IDs, transactions and explicit duplicate handling. Replay reads recorded events without inventing new observations. Exports preserve provenance. Retention has documented row/byte limits and makes pruning visible rather than silently rewriting history.

Future summaries may identify recurring failures, resource pressure and comparable performance changes. AI summaries are interpretations linked to source event IDs.
