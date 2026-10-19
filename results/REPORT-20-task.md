# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 20 | 12 | 60.0% | 1.000 | 10.246 | 167.000 | 148.150 |
| `baseline_retry` | 20 | 18 | 90.0% | 1.350 | 16.169 | 239.150 | 222.950 |
| `cdavc` | 20 | 17 | 85.0% | 1.350 | 16.441 | 230.500 | 228.850 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 20 | 0.300 | [0.094, 0.506] |
| `cdavc` − `baseline_single` | 20 | 0.250 | [0.055, 0.445] |

## Measured result

Measured result: CD-AVC shows a measured pass-rate gain of 0.250 (25.0 percentage points; 95% CI [0.055, 0.445]). This statement uses only completed paired records; it is not a projection.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 20 | 5.923 | 41.1% | 146.950 |
| `cdavc` | 20 | 6.195 | 47.4% | 144.200 |

## Measured cage-hurt cases

None measured.
