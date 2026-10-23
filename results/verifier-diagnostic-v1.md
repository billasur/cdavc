# Frozen-candidate verifier diagnostic

Fixed, intentionally constructed adversarial candidate fixtures; not held-out model or market evidence.

Fixture configuration SHA-256: `54e61c70bebd1656abad064099dadf366f10ec9e6e2c50574053b093b513a891`
Report SHA-256: `ca1b3060f74ce4b26f17a6ca896f654ab7d35282abb272cee5e8aca2f7955696`

| Contract | Wrong acceptances / incorrect | Correct rejections / correct | Inconclusive | Environment | Coverage |
| --- | --- | --- | --- | --- | --- |
| coarse | 6/6 (100.0%) | 0/4 (0.0%) | 0 | 0 | 100.0% |
| properties | 0/6 (0.0%) | 0/4 (0.0%) | 0 | 0 | 100.0% |

Acceptance criterion met: **True**.
Correct-rejection rate increase allowed: 0.0%.
Measured property-minus-coarse deltas: `{"correct_rejection_rate":0.0,"correct_rejections":0,"wrong_acceptance_rate":-1.0,"wrong_acceptances":-6}`.

## Limitations

- Results describe only these labelled examples and declared checks; they do not estimate generalization or model quality.
- Ground truth is supplied by fixture authors, not inferred by the verifier.
- Fresh temporary projects and subprocesses are isolation, not sandboxing arbitrary Python; use trusted fixtures only.
- Rates use all fixtures of the relevant truth class; inconclusive and environmental outcomes are reported separately.
- Reproducibility assumes the same Python/runtime and verifier version; timing and temporary paths are excluded.

## Case evidence

- good-validation (correct=True): Correct negative-input validation
  - coarse: accepted_under_declared_checks; artifact `92fab6c43d88dc348d36781ee56179444980b9b7c36da2822579ef30c772a592`; evidence `dbca6a0082c7c082a2fcc375e38ccf43c9e9dcceb3695b3ea5f672511fe1dfc5`
  - properties: accepted_under_declared_checks; artifact `92fab6c43d88dc348d36781ee56179444980b9b7c36da2822579ef30c772a592`; evidence `95f71c0d06d7fd2c35e43b1e531acaee17360c06f6f6b8a55a12ddff9d00c707`
- good-duplicates (correct=True): Correct duplicate preservation and non-mutation
  - coarse: accepted_under_declared_checks; artifact `96048ef8f9b2bfa6a519219bff2194350275ef39fc73394de69745034ec297d4`; evidence `f4b92e1d43daa30a92d3615488f22b9862ba190af4a65021c0579757154ce2a5`
  - properties: accepted_under_declared_checks; artifact `96048ef8f9b2bfa6a519219bff2194350275ef39fc73394de69745034ec297d4`; evidence `d09f83761f56d58ef765de2af73f1091c79aead704b7d8f9c5530738330a2b7f`
- good-boundary (correct=True): Correct zero and singleton boundaries
  - coarse: accepted_under_declared_checks; artifact `d568a3fcbda1455b6e53ff433b7b8ccc3b8d789620a14a78315d2ef8494d538b`; evidence `9537cdf6e303c96923dd62b389ec5167e644c6d89333fe1731b37cfd02651ea2`
  - properties: accepted_under_declared_checks; artifact `d568a3fcbda1455b6e53ff433b7b8ccc3b8d789620a14a78315d2ef8494d538b`; evidence `420fc15aef9d162233483e13a58e84b88bbecf7b2b63e76cb587d72eee783313`
- good-modules (correct=True): Correct implementation across multiple modules
  - coarse: accepted_under_declared_checks; artifact `439fd9bb39c388d4991b75059c4d507dadd70cdbf64edc9e7ee11894fe21ddaf`; evidence `9b0d7696f2c2720e8cd45d93907e443d55684c2733f512922aca7493b42fde31`
  - properties: accepted_under_declared_checks; artifact `439fd9bb39c388d4991b75059c4d507dadd70cdbf64edc9e7ee11894fe21ddaf`; evidence `2366268fb54986281c4bbd85b618e1d8f592a9b943c63d139d03a936cbc006f5`
- unreachable-raise (correct=False): Incorrect unreachable validation raise
  - coarse: accepted_under_declared_checks; artifact `f2004640eea8a3c3386d9859b1959316c48cda155f35b2db47bff79577342cf1`; evidence `db29bc815faa2f18b31c7a2995dd30b503416327e4dea369b22c20d169135b09`
  - properties: rejected_with_counterexample; artifact `f2004640eea8a3c3386d9859b1959316c48cda155f35b2db47bff79577342cf1`; evidence `939a70b46a0c02981520815cc8fbdb659d6b13ab383f35f961c340b1c1d008a2`
- unrelated-raise (correct=False): Incorrect unrelated helper raise
  - coarse: accepted_under_declared_checks; artifact `cebc74ae3f6b44288213da2204bbdb167d792505208215a1d19724fa6cf9443c`; evidence `5836320a4033a1a3ccdd3160fb62fe30701c4f0793dcb94b57a4c5d6e430b5cc`
  - properties: rejected_with_counterexample; artifact `cebc74ae3f6b44288213da2204bbdb167d792505208215a1d19724fa6cf9443c`; evidence `fd7e7a0c44e5962f2d3488e4dc18ba27741ac21253bbb2c2927517f6493a7b15`
- wrong-exception (correct=False): Incorrect exception type on negative input
  - coarse: accepted_under_declared_checks; artifact `be8eff9bcaa69aac4fb540447e55db5763bc4406f6c55f42a5b838335021242e`; evidence `725c0adc2f4326ffa928deac9b6557f8c15ad9f193b30f77ef17ccf25880bb4d`
  - properties: rejected_with_counterexample; artifact `be8eff9bcaa69aac4fb540447e55db5763bc4406f6c55f42a5b838335021242e`; evidence `054770df95fd04bde592b93882d3218fd835ef41307d644a62b441841440cfb0`
- drops-duplicates (correct=False): Incorrect set-based duplicate loss
  - coarse: accepted_under_declared_checks; artifact `6a3cc8c43e82f529fcd328cf6217b0637b13976c902ca8ce2e4cb46a8add9f38`; evidence `50754144b2582120fbc509e506c29c971d569aaae22171d3d64d2f174635c1c6`
  - properties: rejected_with_counterexample; artifact `6a3cc8c43e82f529fcd328cf6217b0637b13976c902ca8ce2e4cb46a8add9f38`; evidence `39a33e944d699453149562fa21bd9b1cf200b35890726cb38140fb03d614bd48`
- mutates-input (correct=False): Incorrect in-place sort mutates input
  - coarse: accepted_under_declared_checks; artifact `80483245369b28403c997ca55e76beec9e2b9ab94a05bd1ea0debc8b5523ec08`; evidence `17f471ff7c077f2ff48ea16ca9403c5b8ed9f3f39bbc74b221c3eb95618fa8c6`
  - properties: rejected_with_counterexample; artifact `80483245369b28403c997ca55e76beec9e2b9ab94a05bd1ea0debc8b5523ec08`; evidence `34c59eac7cf176a7c46e49281c98c6656fe13533d615b37acc92bf8ee92c82b4`
- bad-zero-boundary (correct=False): Incorrect special case at zero boundary
  - coarse: accepted_under_declared_checks; artifact `ca9e05f69be1e9d497aa257257faf6e35dbe84c72bd67096a77c4dc6e3e310a5`; evidence `ecd5d8dc47ddcbd0e794341ae04d34596c61ff170d77420420c849df67739574`
  - properties: rejected_with_counterexample; artifact `ca9e05f69be1e9d497aa257257faf6e35dbe84c72bd67096a77c4dc6e3e310a5`; evidence `d20a552572000b2e71b8eda8080fd261726549e5a34a196cb06e51e28615a855`
