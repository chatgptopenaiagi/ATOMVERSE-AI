# Interoperability

ARX, COG, DRAGONHYDRA and Qwen remain independent. Inspect their actual interfaces before reuse. Prefer versioned JSON exports, documented CLI operations and configurable loopback model endpoints.

Do not import arbitrary modules from sibling projects or modify their installations. A source path is provenance, not executable instruction. Environment discovery must not activate or change global environments. Keep GPU runtime selection explicit.
