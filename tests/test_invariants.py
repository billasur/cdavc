"""Unit tests for the invariant-to-AST mapping helpers."""

from __future__ import annotations

import ast
import unittest

from cdavc.invariants import raises_exception, required_exception


class RequiredExceptionTests(unittest.TestCase):
    def test_reads_named_error_class(self):
        self.assertEqual(
            required_exception(["Raise ValueError when size is not positive."]),
            "ValueError",
        )

    def test_ignores_prose_without_a_class_name(self):
        self.assertIsNone(required_exception(["raise an error for empty input"]))

    def test_no_invariants(self):
        self.assertIsNone(required_exception([]))


class RaisesExceptionTests(unittest.TestCase):
    def parse(self, source: str) -> ast.AST:
        return ast.parse(source)

    def test_matches_plain_raise(self):
        tree = self.parse("def f():\n    raise ValueError\n")
        self.assertTrue(raises_exception(tree, "ValueError"))

    def test_matches_raise_call(self):
        tree = self.parse("def f():\n    raise ValueError('bad input')\n")
        self.assertTrue(raises_exception(tree, "ValueError"))

    def test_matches_attribute_form(self):
        tree = self.parse("import errors\ndef f():\n    raise errors.ValueError('bad input')\n")
        self.assertTrue(raises_exception(tree, "ValueError"))

    def test_rejects_other_exception_class(self):
        tree = self.parse("def f():\n    raise TypeError('wrong class')\n")
        self.assertFalse(raises_exception(tree, "ValueError"))

    def test_bare_reraise_does_not_count(self):
        tree = self.parse("def f():\n    try:\n        g()\n    except KeyError:\n        raise\n")
        self.assertFalse(raises_exception(tree, "ValueError"))

    def test_no_raise_at_all(self):
        tree = self.parse("def f():\n    return 42\n")
        self.assertFalse(raises_exception(tree, "ValueError"))


if __name__ == "__main__":
    unittest.main()
