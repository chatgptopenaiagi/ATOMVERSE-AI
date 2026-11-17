# Component boundaries

| Engine | Input | Output | Failure contract |
|---|---|---|---|
| Intake | Explicit file, text or worker result | Size-bounded source payload | Actionable parse/source error |
| ARX adapter | Supported versioned JSON | Events with units and provenance | Unsupported version/shape |
| Validator | Event record | Validated event | Field-specific error |
| Atomic data | Validated observation | Derived score and classification | Missing metric stays unknown |
| Memory | Validated event/query | Durable history | Transaction rollback |
| Benchmark | Validated bounded configuration | PASS/FAIL/CANCELLED/SKIP event | Captured exception/timeout |
| Simulation | Events and display settings | Bounded object state | Drop visual detail, preserve data |
| Renderer | Object state | Interactive scene | Quality reduction |
| AI | Selected evidence/question | Labeled interpretation | Unavailable/error, no fabricated data |
| Export | Selected stored events | Atomic JSON/CSV file | Preserve previous destination |

Concrete APIs will be documented after architecture selection. Components must be testable without a running GUI.
