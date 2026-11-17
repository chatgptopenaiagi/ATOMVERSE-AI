# System overview

The implemented system is documented in [ATOMVERSE architecture](../ATOMVERSE-ARCHITECTURE.md). Python/Qt, SQLite, explicit ARX intake and isolated benchmark workers form the first verified vertical slice. Intake, validation, storage, simulation, rendering, benchmarking and optional interpretation have separate interfaces. The GUI never treats animation as measurement evidence. The [genesis proposal](../GENESIS-ARCHITECTURE.md) remains the historical starting point.
