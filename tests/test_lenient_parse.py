"""Synthetic unit tests for the opt-in lenient files-object parser.

No stored raw failing responses exist (the harness never saved them), so these
cases are SYNTHETIC examples of plausible malformed outputs, not measured ones.
"""
import json
import unittest

from cdavc.benchmark import _lenient_payload, _strict_payload

F = ["pkg/solution.py"]
CODE = "def f(x):\n    return x\n"


class LenientParse(unittest.TestCase):
    def test_strict_ok_unchanged(self):
        r = json.dumps({"files": {F[0]: CODE}})
        self.assertEqual(_strict_payload(r)["files"][F[0]], CODE)

    def test_prose_around_json(self):
        r = "Here you go:\n" + json.dumps({"files": {F[0]: CODE}}) + "\nHope it helps."
        self.assertEqual(_lenient_payload(r, F)["files"][F[0]], CODE)

    def test_trailing_comma(self):
        r = '{"files": {"pkg/solution.py": "x = 1\\n",}, }'
        self.assertEqual(_lenient_payload(r, F)["files"][F[0]], "x = 1\n")

    def test_bare_path_object(self):
        r = json.dumps({F[0]: CODE})
        self.assertEqual(_lenient_payload(r, F)["files"][F[0]], CODE)

    def test_single_python_block(self):
        r = "```python\n" + CODE + "```"
        self.assertEqual(_lenient_payload(r, F)["files"][F[0]], CODE)

    def test_python_block_ignored_for_multi_file(self):
        self.assertIsNone(_lenient_payload("```python\nx=1\n```", ["a.py", "b.py"]))

    def test_invalid_escape(self):
        r = '{"files": {"pkg/solution.py": "import re\\nre.compile(\'\\d+\')\\n"}}'
        out = _lenient_payload(r, F)
        self.assertIn("\\d+", out["files"][F[0]])

    def test_missing_final_brace(self):
        # shape seen in 4 of 4 captured gpt-oss-20b failures
        r = '{"files": {"pkg/solution.py": "x = 1\\n"}'
        self.assertIsNone(_strict_payload(r))
        self.assertEqual(_lenient_payload(r, F)["files"][F[0]], "x = 1\n")

    def test_bracket_instead_of_brace(self):
        # shape seen in a real gpt-oss-20b failure (dev2 e13): ends with "}]"
        r = '{"files": {"pkg/solution.py": "x = 1\\n"}]'
        self.assertIsNone(_strict_payload(r))
        self.assertEqual(_lenient_payload(r, F)["files"][F[0]], "x = 1\n")

    def test_garbage_is_none(self):
        self.assertIsNone(_lenient_payload("I cannot do that.", F))
        self.assertIsNone(_lenient_payload("", F))

    def test_two_blocks_not_guessed(self):
        self.assertIsNone(_lenient_payload("```python\na=1\n```\n```python\nb=2\n```", F))


if __name__ == "__main__":
    unittest.main()


class StoredRealFailures(unittest.TestCase):
    """Real raw failures captured on gpt-oss-20b (dev2, t=0.7). Skipped if results are absent."""

    def test_real_raw_failures(self):
        import glob
        files = glob.glob("results/groq/openai_gpt-oss-20b/1-dev2-t0.7-*/raw_failures.jsonl")
        rows = [json.loads(line) for f in files for line in open(f)]
        if not rows:
            self.skipTest("no stored raw failures")
        recovered = 0
        for row in rows:
            self.assertIsNone(_strict_payload(row["raw"]))
            recovered += _lenient_payload(row["raw"], ["x.py"]) is not None
        self.assertGreaterEqual(recovered, len(rows) - 1)
