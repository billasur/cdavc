# CD-AVC benchmark report

All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.
Budget disclosure: differing draw limits and incomplete telemetry are not matched-token evidence. These summaries do not establish model superiority or token savings. Use the explicit-cap external comparison workflow for qualified frozen-artifact comparisons.

Fairness disclosure: public checks alone select candidates. Held-out scoring runs once after selection, never triggers another generation, and never feeds a repair prompt. Acceptance and held-out success are recorded separately. All arms use the same initial prompt and common final evaluator; retries and independent samples have different draw budgets.

| Arm | Records | Passed | Pass rate | 95% CI (Wilson) | Mean attempts | Mean wall (s) | Mean token in | Mean token out |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| `baseline_single` | 50 | 50 | 100.0% | [0.929, 1.000] | 1.000 | 1.384 | — | — |
| `baseline_retry` | 50 | 50 | 100.0% | [0.929, 1.000] | 1.000 | 1.381 | — | — |
| `cdavc` | 50 | 50 | 100.0% | [0.929, 1.000] | 1.000 | 1.759 | — | — |
| `cdavc_sampled` | 50 | 50 | 100.0% | [0.929, 1.000] | 1.000 | 1.749 | — | — |
| `cdavc_sampled_repair` | 50 | 50 | 100.0% | [0.929, 1.000] | 1.000 | 1.749 | — | — |

## Paired pass-rate differences

| Comparison | N | Difference | 95% CI |
|---|---:|---:|---:|
| `baseline_retry` − `baseline_single` | 50 | 0.000 | [0.000, 0.000] |
| `cdavc` − `baseline_single` | 50 | 0.000 | [0.000, 0.000] |
| `cdavc_sampled` − `baseline_single` | 50 | 0.000 | [0.000, 0.000] |
| `cdavc_sampled` − `baseline_retry` | 50 | 0.000 | [0.000, 0.000] |
| `cdavc_sampled` − `cdavc` | 50 | 0.000 | [0.000, 0.000] |
| `cdavc_sampled_repair` − `baseline_single` | 50 | 0.000 | [0.000, 0.000] |
| `cdavc_sampled_repair` − `baseline_retry` | 50 | 0.000 | [0.000, 0.000] |
| `cdavc_sampled_repair` − `cdavc` | 50 | 0.000 | [0.000, 0.000] |
| `cdavc_sampled_repair` − `cdavc_sampled` | 50 | 0.000 | [0.000, 0.000] |

## Measured result

Measured result: `cdavc_sampled` shows no measured pass-rate gain of 0.000 (0.0 percentage points vs `baseline_single`; 95% CI [0.000, 0.000]). This statement uses only completed paired records; it is not a projection.
Measured result: `cdavc_sampled_repair` shows no measured pass-rate gain of 0.000 (0.0 percentage points vs `baseline_single`; 95% CI [0.000, 0.000]). This statement uses only completed paired records; it is not a projection.
Measured result: `cdavc` shows no measured pass-rate gain of 0.000 (0.0 percentage points vs `baseline_single`; 95% CI [0.000, 0.000]). This statement uses only completed paired records; it is not a projection.
Measured result: `cdavc_sampled` shows no measured pass-rate gain of 0.000 (0.0 percentage points vs `baseline_retry`; 95% CI [0.000, 0.000]). This statement uses only completed paired records; it is not a projection.
Measured result: `cdavc_sampled_repair` shows no measured pass-rate gain of 0.000 (0.0 percentage points vs `cdavc_sampled`; 95% CI [0.000, 0.000]). This statement uses only completed paired records; it is not a projection.

## Sampling budget

| Arm | Draw budget | Mean draws used | Mean draws to accept | JSON re-asks |
|---|---:|---:|---:|---:|
| `baseline_single` | 1.000 | 1.000 | 1.000 | 0 |
| `baseline_retry` | 3.000 | 1.000 | 1.000 | 0 |
| `cdavc` | 3.000 | 1.000 | 1.000 | 0 |
| `cdavc_sampled` | 4.000 | 1.000 | 1.000 | 0 |
| `cdavc_sampled_repair` | 4.000 | 1.000 | 1.000 | 0 |

## Measured overhead vs baseline_single

| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |
|---|---:|---:|---:|---:|
| `baseline_retry` | 50 | -0.003 | -0.2% | — |
| `cdavc` | 50 | 0.375 | 27.2% | — |
| `cdavc_sampled` | 50 | 0.365 | 26.5% | — |
| `cdavc_sampled_repair` | 50 | 0.365 | 26.5% | — |

## Measured verifier gap

None measured: no cage candidate passed the public gates and then failed the hidden gate.

## Measured failure categories

None measured: every recorded arm passed its task.

## Measured cage-hurt cases

None measured.
