# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 30 | 16 | 53.3% | 1.000 | 13.756 | 166.800 | 166.933 |
| `baseline_retry` | 30 | 24 | 80.0% | 1.600 | 21.564 | 287.600 | 271.533 |
| `cdavc` | 30 | 23 | 76.7% | 1.533 | 24.262 | 280.367 | 290.567 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 30 | 0.267 | [0.080, 0.453] |
| `cdavc` − `baseline_single` | 30 | 0.233 | [0.079, 0.387] |

## Measured result

Measured result: CD-AVC shows a measured pass-rate gain of 0.233 (23.3 percentage points; 95% CI [0.079, 0.387]). This statement uses only completed paired records; it is not a projection.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 30 | 7.807 | 45.3% | 225.400 |
| `cdavc` | 30 | 10.506 | 69.1% | 237.200 |

## Measured cage-hurt cases

None measured.
