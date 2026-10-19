# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 4 | 4 | 100.0% | 1.000 | 80.352 | 393.250 | 1273.750 |
| `baseline_retry` | 4 | 4 | 100.0% | 1.000 | 59.631 | 393.250 | 1941.000 |
| `cdavc` | 4 | 4 | 100.0% | 1.500 | 90.587 | 617.750 | 3110.250 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 4 | 0.000 | [0.000, 0.000] |
| `cdavc` − `baseline_single` | 4 | 0.000 | [0.000, 0.000] |

## Measured result

Measured result: CD-AVC shows no measured pass-rate gain of 0.000 (0.0 percentage points; 95% CI [0.000, 0.000]). This statement uses only completed paired records; it is not a projection.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 4 | -20.722 | 49.8% | 667.250 |
| `cdavc` | 4 | 10.234 | 1287.3% | 2061.000 |

## Measured cage-hurt cases

None measured.
