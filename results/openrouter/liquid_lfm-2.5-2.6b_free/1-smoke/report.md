# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 2 | 1 | 50.0% | 1.000 | 11.649 | 335.000 | 1502.000 |
| `baseline_retry` | 2 | 1 | 50.0% | 2.000 | 24.360 | 336.000 | 1397.000 |
| `cdavc` | 2 | 1 | 50.0% | 2.500 | 27.308 | 684.000 | 3487.000 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 2 | 0.000 | [0.000, 0.000] |
| `cdavc` − `baseline_single` | 2 | 0.000 | [0.000, 0.000] |

## Measured result

Measured result: CD-AVC shows no measured pass-rate gain of 0.000 (0.0 percentage points; 95% CI [0.000, 0.000]). This statement uses only completed paired records; it is not a projection.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 2 | 12.711 | 71.2% | -104.000 |
| `cdavc` | 2 | 15.659 | 125.7% | 2334.000 |

## Measured cage-hurt cases

None measured.
