# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 8 | 6 | 75.0% | 1.000 | 8.405 | 437.000 | 831.500 |
| `baseline_retry` | 8 | 8 | 100.0% | 1.375 | 16.087 | 615.125 | 1112.625 |
| `baseline_fresh` | 0 | 0 | — | — | — | — | — |
| `cdavc` | 8 | 7 | 87.5% | 1.500 | 21.456 | 695.125 | 1342.750 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 8 | 0.250 | [-0.071, 0.571] |
| `cdavc` − `baseline_single` | 8 | 0.125 | [-0.120, 0.370] |

## Measured result

Measured result: CD-AVC shows a measured positive difference, but not a conclusive gain because the 95% CI includes zero of 0.125 (12.5 percentage points; 95% CI [-0.120, 0.370]). This statement uses only completed paired records; it is not a projection.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 8 | 7.682 | 769.2% | 459.250 |
| `cdavc` | 8 | 13.050 | 554.6% | 769.375 |

## Measured cage-hurt cases

None measured.
