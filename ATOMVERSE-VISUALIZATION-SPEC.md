# Measured universe mapping

The workstation nucleus and eight component orbits remain. CPU cores are labeled nodes; processes occupy the code orbit. RAM/storage fill percentages affect their structures. NVIDIA device load drives the GPU constellation. Stable entity IDs determine starting positions, so new samples update the same entity.

Intensity = clamp((value − lower) / (upper − lower), 0, 1). Visual energy = intensity × confidence × display scale. Utilization/fill percentages normalize over 0–100. Rotation uses `phase × visual_energy × 0.42`; radius uses `3 + 5.5 × visual_energy` before projection. The nucleus uses mean visible energy. These are dimensionless rendering properties, not physical energy. Display settings never alter measurements.

Schema 1.1 uses blue OBSERVED circles, green DERIVED circles, purple AI_INTERPRETED squares, amber SIMULATED squares and gray UNAVAILABLE circles. Failures retain red. Mixed observed/derived records expose each metric's classification in tables and the inspector. Legacy 1.0 retains its mapping and explicit data-kind classification. Demo, live, recorded and replay have persistent distinct badges.

Dotted connections exist only for recorded relationships with visible endpoints. Full targets and source APIs remain inspectable when an endpoint is outside the scene. CPU/memory use, parent identity, hashed executable identity and supported NVIDIA context membership are separate types. No dependency is inferred from coincidental activity. Historical and terminated process states are explicit.

Selecting a particle reveals ID, source, timestamp, values, units, status, formulas, unavailable reasons, relationships and up to 12 retained entity-history records. Tables support sorting, text/class/outcome filtering and a start-time filter. Replay offers ordered timeline navigation. Drag rotates, right drag pans, wheel zooms; arrows and +/- also navigate. Pause motion leaves observation running; Stop live observer ends collection.

Rendering is native Qt software painting with perspective projection. Cached orbit paths, 15/30/60 fps caps, up to 512 particles and adaptive reduction bound work. Visible coverage and skipped display batches are reported. No artistic effect is presented as a measured quantity.
