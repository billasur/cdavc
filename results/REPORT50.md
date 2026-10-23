# CD-AVC benchmark report

> Superseded: this four-arm table is from an earlier harness. The current five-arm measurement of the same 50-task corpus is `REPORT50-PAYLOADS.md`.

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.

Fairness disclosure: `baseline_retry` is the only arm given evaluator output — its second and later prompts contain the failing hidden test's output. Neither cage arm (`cdavc`, `cdavc_sampled`) ever receives hidden-gate output; a cage repair prompt carries public-gate output or the task's declared invariants. Every arm receives the same task prompt, the same model, and its own derived sampling seed per draw.

| Arm | Records | Passed | Pass rate | 95% CI (Wilson) | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| `baseline_single` | 50 | 28 | 56.0% | [0.423, 0.688] | 1.000 | 17.867 | 240.286 | 193.673 |
| `baseline_retry` | 50 | 42 | 84.0% | [0.715, 0.917] | 1.640 | 30.981 | 462.680 | 391.340 |
| `cdavc` | 50 | 35 | 70.0% | [0.562, 0.809] | 1.800 | 29.835 | 477.260 | 369.680 |
| `cdavc_sampled` | 50 | 41 | 82.0% | [0.692, 0.902] | 1.900 | 31.261 | 460.840 | 391.560 |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 50 | 0.280 | [0.154, 0.406] |
| `cdavc` − `baseline_single` | 50 | 0.140 | [0.028, 0.252] |
| `cdavc_sampled` − `baseline_single` | 50 | 0.260 | [0.137, 0.383] |
| `cdavc_sampled` − `baseline_retry` | 50 | -0.020 | [-0.125, 0.085] |
| `cdavc_sampled` − `cdavc` | 50 | 0.120 | [-0.013, 0.253] |

## Measured result

Measured result: `cdavc_sampled` shows a measured pass-rate gain of 0.260 (26.0 percentage points vs `baseline_single`; 95% CI [0.137, 0.383]). This statement uses only completed paired records; it is not a projection.
Measured result: `cdavc` shows a measured pass-rate gain of 0.140 (14.0 percentage points vs `baseline_single`; 95% CI [0.028, 0.252]). This statement uses only completed paired records; it is not a projection.
Measured result: `cdavc_sampled` shows a measured negative pass-rate difference of -0.020 (-2.0 percentage points vs `baseline_retry`; 95% CI [-0.125, 0.085]). This statement uses only completed paired records; it is not a projection.

## Sampling budget

| Arm | Draw budget | Mean draws used | Mean draws to accept | JSON re-asks |
|---|---:|---:|---:|---:|
| `baseline_single` | 1.000 | 1.000 | 1.000 | 5 |
| `baseline_retry` | 3.000 | 1.640 | 1.381 | 14 |
| `cdavc` | 3.000 | 1.800 | 1.286 | 9 |
| `cdavc_sampled` | 4.000 | 1.900 | 1.439 | 8 |

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 50 | 13.114 | 79.9% | 414.490 |
| `cdavc` | 50 | 11.968 | 85.9% | 406.816 |
| `cdavc_sampled` | 50 | 13.393 | 102.1% | 412.837 |

## Measured verifier gap

- `cdavc`: 5 task(s) where at least one candidate passed the public targeted test and was rejected by the hidden gate.
- `cdavc_sampled`: 5 task(s) where at least one candidate passed the public targeted test and was rejected by the hidden gate.

## Measured cage-hurt cases

| Task | baseline_single | cdavc |
|---|---:|---:|
| `task_048` | PASS | FAIL |
