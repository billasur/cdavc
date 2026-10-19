# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 8 | 5 | 62.5% | 1.000 | 21.681 | 437.000 | 914.375 |
| `baseline_retry` | 8 | 7 | 87.5% | 1.500 | 15.270 | 674.750 | 1340.125 |
| `cdavc` | 8 | 8 | 100.0% | 1.250 | 9.224 | 552.625 | 1286.250 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 8 | 0.250 | [-0.240, 0.740] |
| `cdavc` − `baseline_single` | 8 | 0.375 | [0.016, 0.734] |

## Measured result

Measured result: CD-AVC shows a measured pass-rate gain of 0.375 (37.5 percentage points; 95% CI [0.016, 0.734]). This statement uses only completed paired records; it is not a projection.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 8 | -6.411 | 678.2% | 663.500 |
| `cdavc` | 8 | -12.457 | 9.1% | 487.500 |

## Measured cage-hurt cases

None measured.
