# CD-AVC system design

![CD-AVC high-level system design](cdavc-system-design.svg)

The diagram adapts the supplied flow into the v0 boundaries:

1. Cloud planning produces contracts and tests.
2. A test-of-tests audit approves the task graph.
3. A local model writes only implementation-file patches.
4. The supervisor runs AST, targeted-test and regression gates.
5. Declared negative/chaos checks run after the deterministic gates.
6. A pass produces a report; a failure feeds a bounded trace back to repair.

The cloud and local model are not verification authorities. The deterministic
verification cage is the authority for whether a candidate can proceed.
