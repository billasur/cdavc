# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | 95% CI | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 30 | 24 | 80.0% | [0.627, 0.905] | 1.000 | 17.259 | 182.800 | 151.833 |
| `baseline_retry` | 30 | 28 | 93.3% | [0.787, 0.982] | 1.433 | 24.822 | 280.800 | 228.567 |
| `cdavc` | 30 | 25 | 83.3% | [0.664, 0.927] | 1.500 | 43.434 | 656.767 | 287.733 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 30 | 0.133 | [0.010, 0.257] |
| `cdavc` − `baseline_single` | 30 | 0.033 | [-0.115, 0.181] |

## Measured result

Measured result: CD-AVC shows a measured positive difference, but not a conclusive gain because the 95% CI includes zero of 0.033 (3.3 percentage points; 95% CI [-0.115, 0.181]). This statement uses only completed paired records; it is not a projection.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 30 | 7.563 | 45.7% | 174.733 |
| `cdavc` | 30 | 26.175 | 144.2% | 609.867 |

## Sampling and gate metrics

| Arm | Mean samples drawn | Mean samples to accept | Mean distinct failure signatures | JSON re-asks | Static re-asks | Mean properties checked |
|---|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 1.000 | 1.000 | 0.200 | 0 | 0 | — |
| `baseline_retry` | 1.433 | 1.357 | 0.467 | 0 | 0 | — |
| `cdavc` | 1.500 | 1.320 | 0.500 | 3 | 0 | 23.310 |

Measured false-accept rate on the hidden gate: 1 of 25 public-gate passes were rejected by a hidden gate (4.0%).
Measured mutant kill rate: 98.9% of generated defects were rejected by the property gate.

## Measured cage-hurt cases

| Task | baseline_single | cdavc |
|---|---:|---:|
| `task_009` | PASS | FAIL |
| `task_021` | PASS | FAIL |
