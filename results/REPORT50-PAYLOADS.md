# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

Fairness disclosure: `baseline_retry` is the only arm given evaluator output — its second and later prompts contain the failing hidden test's output. No cage arm (`cdavc`, `cdavc_sampled`, `cdavc_sampled_repair`) ever receives hidden-gate output; a cage repair prompt carries public-gate output or the task's declared invariants. Every arm receives the same task prompt, the same model, and its own derived sampling seed per draw.

| Arm | Records | Passed | Pass rate | 95% CI (Wilson) | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| `baseline_single` | 50 | 29 | 58.0% | [0.442, 0.706] | 1.000 | 16.925 | 229.224 | 184.102 |
| `baseline_retry` | 50 | 42 | 84.0% | [0.715, 0.917] | 1.640 | 30.449 | 456.540 | 388.160 |
| `cdavc` | 50 | 36 | 72.0% | [0.583, 0.825] | 1.760 | 28.105 | 450.200 | 346.500 |
| `cdavc_sampled` | 50 | 41 | 82.0% | [0.692, 0.902] | 1.900 | 31.261 | 460.840 | 391.560 |
| `cdavc_sampled_repair` | 50 | 40 | 80.0% | [0.670, 0.888] | 1.960 | 33.497 | 535.940 | 410.480 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 50 | 0.260 | [0.125, 0.395] |
| `cdavc` − `baseline_single` | 50 | 0.140 | [0.028, 0.252] |
| `cdavc_sampled` − `baseline_single` | 50 | 0.240 | [0.120, 0.360] |
| `cdavc_sampled` − `baseline_retry` | 50 | -0.020 | [-0.125, 0.085] |
| `cdavc_sampled` − `cdavc` | 50 | 0.100 | [-0.028, 0.228] |
| `cdavc_sampled_repair` − `baseline_single` | 50 | 0.220 | [0.080, 0.360] |
| `cdavc_sampled_repair` − `baseline_retry` | 50 | -0.040 | [-0.165, 0.085] |
| `cdavc_sampled_repair` − `cdavc` | 50 | 0.080 | [-0.014, 0.174] |
| `cdavc_sampled_repair` − `cdavc_sampled` | 50 | -0.020 | [-0.151, 0.111] |

## Measured result

Measured result: `cdavc_sampled` shows a measured pass-rate gain of 0.240 (24.0 percentage points vs `baseline_single`; 95% CI [0.120, 0.360]). This statement uses only completed paired records; it is not a projection.
Measured result: `cdavc_sampled_repair` shows a measured pass-rate gain of 0.220 (22.0 percentage points vs `baseline_single`; 95% CI [0.080, 0.360]). This statement uses only completed paired records; it is not a projection.
Measured result: `cdavc` shows a measured pass-rate gain of 0.140 (14.0 percentage points vs `baseline_single`; 95% CI [0.028, 0.252]). This statement uses only completed paired records; it is not a projection.
Measured result: `cdavc_sampled` shows a measured negative pass-rate difference of -0.020 (-2.0 percentage points vs `baseline_retry`; 95% CI [-0.125, 0.085]). This statement uses only completed paired records; it is not a projection.
Measured result: `cdavc_sampled_repair` shows a measured negative pass-rate difference of -0.020 (-2.0 percentage points vs `cdavc_sampled`; 95% CI [-0.151, 0.111]). This statement uses only completed paired records; it is not a projection.

## Sampling budget

| Arm | Draw budget | Mean draws used | Mean draws to accept | JSON re-asks |
|---|---:|---:|---:|---:|
| `baseline_single` | 1.000 | 1.000 | 1.000 | 3 |
| `baseline_retry` | 3.000 | 1.640 | 1.381 | 13 |
| `cdavc` | 3.000 | 1.760 | 1.278 | 6 |
| `cdavc_sampled` | 4.000 | 1.900 | 1.439 | 8 |
| `cdavc_sampled_repair` | 4.000 | 1.960 | 1.450 | 8 |

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 50 | 13.524 | 92.9% | 425.612 |
| `cdavc` | 50 | 11.180 | 87.3% | 376.184 |
| `cdavc_sampled` | 50 | 14.336 | 115.3% | 433.469 |
| `cdavc_sampled_repair` | 50 | 16.572 | 115.1% | 529.000 |

## Measured verifier gap

- `cdavc`: 5 task(s) where at least one candidate passed the public targeted test and was rejected by the hidden gate.
- `cdavc_sampled`: 5 task(s) where at least one candidate passed the public targeted test and was rejected by the hidden gate.
- `cdavc_sampled_repair`: 9 task(s) where at least one candidate passed the public targeted test and was rejected by the hidden gate.

## Measured failure categories

| Category | `baseline_single` | `baseline_retry` | `cdavc` | `cdavc_sampled` | `cdavc_sampled_repair` |
|---|---:|---:|---:|---:|---:|
| baseline hidden test failed | 20 | 8 | 0 | 0 | 0 |
| targeted test failed | 0 | 0 | 9 | 7 | 4 |
| hidden test failed | 0 | 0 | 2 | 1 | 4 |
| AST Contract Failed | 0 | 0 | 2 | 1 | 2 |
| boundary probe failed | 0 | 0 | 1 | 0 | 0 |
| provider unavailable | 1 | 0 | 0 | 0 | 0 |

## Measured cage-hurt cases

| Task | baseline_single | cdavc |
|---|---:|---:|
| `task_048` | PASS | FAIL |
