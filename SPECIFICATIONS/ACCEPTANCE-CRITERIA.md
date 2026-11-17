# Acceptance criteria

## Stage 1 gate

- Public repository belongs to chatgptopenaiagi.
- Initial commit is conceptual documentation, with preserved human vision and roadmap.
- Remote default branch, README, vision and roadmap are read back.
- Published files contain no credentials or raw private machine data.
- Sanitized verification reports exist.

## Stage 2 vertical slice

| Requirement | Required evidence |
|---|---|
| Windows launch and interactive universe | Actual packaged executable, screenshot and interaction checks |
| Real ARX ingestion | Actual supported report, normalized values and provenance |
| Data-driven objects | Selected object resolves to exact event/measurement |
| Accurate tables | Values checked against normalized input |
| SQLite persistence | Reopen and compare records |
| CPU benchmark | Bounded real execution, numeric verification and saved result |
| GPU benchmark when supported | Runtime/device confirmation, synchronization and numeric verification |
| Replay | Stored order, isolation from live/demo and bounded controls |
| JSON export | Reimport/readback preserves values |
| Errors | Malformed input and failed benchmark accurately displayed |
| Clean shutdown | Worker termination and database integrity |
| Preservation | No modifications to existing installations or sibling repositories |

Tests also cover schema, normalization, energy equations, units, exports, environment discovery, GUI lifecycle, rendering performance, resource limits and data permissions. Functional tests inspect outputs. Missing checks remain explicitly unverified.

The ten long-term views and broad benchmark categories may be staged after the verified slice. Do not equate a build artifact with release readiness.
