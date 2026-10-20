# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

| Arm | Records | Passed | Pass rate | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 0 | 0 | — | — | — | — | — |
| `baseline_retry` | 3 | 2 | 66.7% | 2.333 | 22.021 | 1336.667 | 2538.667 |
| `baseline_fresh` | 0 | 0 | — | — | — | — | — |
| `cdavc` | 0 | 0 | — | — | — | — | — |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 0 | — | — |
| `cdavc` − `baseline_single` | 0 | — | — |

## Measured result

Measured result: no paired `cdavc`/`baseline_single` records were available.

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 0 | — | — | — |
| `cdavc` | 0 | — | — | — |

## Measured cage-hurt cases

None measured.
