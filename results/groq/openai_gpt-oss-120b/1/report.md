# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 8 | 8 | 100.0% | 1.000 | 14.931 | 437.000 | 741.250 |
| `baseline_retry` | 8 | 8 | 100.0% | 1.000 | 1.960 | 437.000 | 741.500 |
| `cdavc` | 8 | 8 | 100.0% | 1.000 | 14.190 | 438.000 | 727.750 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 8 | 0.000 | [0.000, 0.000] |
| `cdavc` − `baseline_single` | 8 | 0.000 | [0.000, 0.000] |

## Measured result

Measured result: CD-AVC shows no measured pass-rate gain of 0.000 (0.0 percentage points; 95% CI [0.000, 0.000]). This statement uses only completed paired records; it is not a projection.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 8 | -12.971 | -33.1% | 0.250 |
| `cdavc` | 8 | -0.742 | 271.4% | -12.500 |

## Measured cage-hurt cases

None measured.
