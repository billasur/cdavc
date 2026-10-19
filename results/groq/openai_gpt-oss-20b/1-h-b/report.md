# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 8 | 3 | 37.5% | 1.000 | 8.105 | 437.000 | 867.000 |
| `baseline_retry` | 8 | 7 | 87.5% | 1.500 | 22.077 | 687.750 | 1212.125 |
| `cdavc` | 8 | 8 | 100.0% | 1.375 | 16.089 | 607.875 | 1196.625 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 8 | 0.500 | [0.130, 0.870] |
| `cdavc` − `baseline_single` | 8 | 0.625 | [0.266, 0.984] |

## Measured result

Measured result: CD-AVC shows a measured pass-rate gain of 0.625 (62.5 percentage points; 95% CI [0.266, 0.984]). This statement uses only completed paired records; it is not a projection.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 8 | 13.973 | 1583.9% | 595.875 |
| `cdavc` | 8 | 7.985 | 856.6% | 500.500 |

## Measured cage-hurt cases

None measured.
