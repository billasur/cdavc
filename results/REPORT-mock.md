# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 30 | 30 | 100.0% | 1.000 | 0.090 | — | — |
| `baseline_retry` | 30 | 30 | 100.0% | 1.000 | 0.090 | — | — |
| `cdavc` | 30 | 30 | 100.0% | 1.000 | 0.163 | — | — |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 30 | 0.000 | [0.000, 0.000] |
| `cdavc` − `baseline_single` | 30 | 0.000 | [0.000, 0.000] |

## Measured result

Measured result: CD-AVC shows no measured pass-rate gain of 0.000 (0.0 percentage points; 95% CI [0.000, 0.000]). This statement uses only completed paired records; it is not a projection.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 30 | -0.000 | 1.0% | — |
| `cdavc` | 30 | 0.073 | 84.5% | — |

## Measured cage-hurt cases

None measured.
