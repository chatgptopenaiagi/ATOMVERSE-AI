# Information to visual energy

Let x be an observed metric in declared units, L/U a documented normalization range, c measurement confidence in [0,1], and s an operator-selected display scale in [0,1].

n = clamp((x - L) / (U - L), 0, 1), with U > L.  
visual_energy = n × c × s.

The score is dimensionless. Missing metrics remain missing and must not be silently treated as zero measurements. An event may still appear as a low-intensity information node without claiming measured load.

Raw metrics, calculation inputs and visual outputs are separate. Color communicates event type and outcome; a failed operation cannot receive a success appearance. Red errors, green verified executions, gold verified benchmarks, blue inputs and white knowledge nodes are proposed semantics.
