import json
import unittest

from cdavc.payloads import parse_payload, strip_json_fence


FENCED = """```json
{"files": {"solution.py": "def add(a, b):\\n    return a + b\\n"}}
```"""

RAW_NEWLINES = '''{"files": {"solution.py": "def add(a, b):
    return a + b
"}}'''

REGEX_ESCAPE = '{"files": {"solution.py": "import re\\n\\npattern = re.compile(r"(\\d+)s")\\n"}}'

UNESCAPED_QUOTES = '''```json
{
  "files": {
    "solution.py": "def parse(text):
    if not text:
        raise ValueError("Empty text")
    match = re.fullmatch(r"(?P<days>\\\\d+)d", text)
    if not match:
        raise ValueError("Unparsable duration format")
    return int(match.group("days"))
"
  }
}
```'''


class PayloadTests(unittest.TestCase):
    def test_plain_fenced_payload_decodes(self):
        self.assertEqual(parse_payload(FENCED), {"files": {"solution.py": "def add(a, b):\n    return a + b\n"}})

    def test_raw_newlines_inside_string_decode(self):
        payload = parse_payload(RAW_NEWLINES)

        self.assertEqual(payload["files"]["solution.py"], "def add(a, b):\n    return a + b\n")

    def test_invalid_regex_escape_is_repaired(self):
        payload = parse_payload(REGEX_ESCAPE)

        self.assertEqual(payload["files"]["solution.py"], 'import re\n\npattern = re.compile(r"(\\d+)s")\n')

    def test_unescaped_interior_quotes_recover_exact_content(self):
        payload = parse_payload(UNESCAPED_QUOTES)

        content = payload["files"]["solution.py"]
        self.assertIn('raise ValueError("Empty text")', content)
        self.assertIn('return int(match.group("days"))', content)
        self.assertTrue(content.endswith("return int(match.group(\"days\"))\n"))
        self.assertEqual(content.count('raise ValueError'), 2)

    def test_quote_followed_by_comma_does_not_truncate_content(self):
        reply = '{"files": {"a.py": "VALUES = ("x", "y")\\nprint(VALUES)\\n"}}'

        payload = parse_payload(reply)

        self.assertEqual(payload["files"]["a.py"], 'VALUES = ("x", "y")\nprint(VALUES)\n')

    def test_edits_payload_with_interior_quotes_decodes(self):
        reply = (
            '```json\n{"edits": [{"file": "a.py", "find": "return name", '
            '"replace": "return name.strip() or "unknown""}]}\n```'
        )

        payload = parse_payload(reply)

        self.assertEqual(payload["edits"][0]["replace"], 'return name.strip() or "unknown"')

    def test_trailing_prose_after_object_is_ignored(self):
        reply = '{"files": {"a.py": "x = 1\\n"}}\n\nThis implementation handles the edge cases.'

        self.assertEqual(parse_payload(reply)["files"]["a.py"], "x = 1\n")

    def test_trailing_prose_after_unescaped_quotes_is_ignored(self):
        reply = UNESCAPED_QUOTES.replace("```", "") + "\n\nNote: the regex is anchored with fullmatch."

        content = parse_payload(reply)["files"]["solution.py"]

        self.assertIn('raise ValueError("Empty text")', content)
        self.assertTrue(content.endswith('return int(match.group("days"))\n'))

    def test_prose_before_object_is_dropped(self):
        reply = 'Here is the patch:\n{"files": {"a.py": "x = 1\\n"}}'

        self.assertEqual(parse_payload(reply)["files"]["a.py"], "x = 1\n")

    def test_example_before_answer_yields_the_answer(self):
        """A reply that shows an example first must not hand the example to the gates."""

        reply = (
            'Example: {"files": {"old.py": "print(1)\\n"}}\n'
            'Answer: {"files": {"new.py": "print(2)\\n"}}'
        )

        self.assertEqual(parse_payload(reply), {"files": {"new.py": "print(2)\n"}})

    def test_top_level_array_is_returned_whole(self):
        reply = '[{"files": {"a.py": "1"}}, {"files": {"b.py": "2"}}]'

        self.assertEqual(parse_payload(reply), [{"files": {"a.py": "1"}}, {"files": {"b.py": "2"}}])

    def test_deeply_nested_reply_raises_instead_of_recursing(self):
        reply = '{"files": ' + "[" * 2000 + "]" * 2000 + "}"

        with self.assertRaises(ValueError):
            parse_payload(reply)

    def test_triple_quoted_value_becomes_json_string(self):
        reply = '{"files": {"a.py": """print("hi")\n"""}}'

        self.assertEqual(parse_payload(reply)["files"]["a.py"], 'print("hi")\n')

    def test_unrecoverable_reply_raises(self):
        with self.assertRaises(ValueError):
            parse_payload("I cannot help with that request.")

    def test_empty_reply_raises(self):
        with self.assertRaises(ValueError):
            parse_payload("")

    def test_non_text_reply_raises(self):
        with self.assertRaises(ValueError):
            parse_payload(None)

    def test_strip_json_fence_returns_bare_object(self):
        stripped = strip_json_fence(FENCED)

        self.assertTrue(stripped.startswith("{"))
        self.assertTrue(stripped.endswith("}"))
        self.assertNotIn("```", stripped)


if __name__ == "__main__":
    unittest.main()
