"""Self-improvement loop for the CD-AVC harness.

The harness (config knobs) is the editable surface. The evaluator
(self_improve/protected/ and the dev2 task tests) is fixed and must stay
outside the improving agent's write access. See docs/SELF_IMPROVE.md.
"""
