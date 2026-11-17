# Genesis architecture

**Status: proposal before discovery.**

Explicit sources → intake → absorption/validation → normalized events → atomic data engine → SQLite memory → simulation → visualization → human inspection.

Bounded benchmark workers and optional AI interpretation feed events through the same validated boundary. Sources include operator-selected ARX exports, typed input, selected code and authorized execution evidence. Telemetry is visible and opt-in.

Components communicate with versioned event records. Observation, calculation, interpretation and simulation are distinct. Rendering can be paused or simplified without changing measurements. Storage is bounded and retains provenance.

No graphics engine or implementation language has been selected before Stage 1 remote verification. See [component boundaries](ARCHITECTURE/COMPONENT-BOUNDARIES.md) and [acceptance criteria](SPECIFICATIONS/ACCEPTANCE-CRITERIA.md).
