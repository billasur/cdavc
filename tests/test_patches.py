import difflib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cdavc.patches import unified_diff_payload


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old = ''.join(f'line {i}\n' for i in range(30))
        (self.root / 'a.py').write_text(self.old)
        (self.root / 'b.py').write_text('before\n')

    def diff(self, old, new, name='a.py'):
        return ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                            fromfile='a/' + name, tofile='b/' + name, n=2))

    def test_multiple_hunks_and_files_without_writes(self):
        new = self.old.replace('line 1\n', 'first\nextra\n').replace('line 27\n', 'last\n')
        text = self.diff(self.old, new) + self.diff('before\n', 'after\n', 'b.py')
        with patch.object(Path, 'write_bytes', side_effect=AssertionError('write')), \
                patch.object(Path, 'write_text', side_effect=AssertionError('write')):
            payload = unified_diff_payload(self.root, ['a.py', 'b.py'], text)
        self.assertEqual(payload, {'files': {'a.py': new, 'b.py': 'after\n'}})
        self.assertEqual((self.root / 'a.py').read_text(), self.old)
        self.assertEqual((self.root / 'b.py').read_text(), 'before\n')

    def test_stale_last_file_is_rejected_without_partial_effect(self):
        text = self.diff(self.old, 'replacement\n') + self.diff('stale\n', 'after\n', 'b.py')
        with self.assertRaises(ValueError):
            unified_diff_payload(self.root, ['a.py', 'b.py'], text)
        self.assertEqual((self.root / 'a.py').read_text(), self.old)
        self.assertEqual((self.root / 'b.py').read_text(), 'before\n')

    def test_git_new_file_and_no_newline(self):
        text = ('diff --git a/new.py b/new.py\nnew file mode 100644\n'
                'index 0000000..1234567\n--- /dev/null\n+++ b/new.py\n'
                '@@ -0,0 +1,2 @@\n+first\n+tail\n\\ No newline at end of file\n')
        self.assertEqual(unified_diff_payload(self.root, ['new.py'], text),
                         {'files': {'new.py': 'first\ntail'}})
        self.assertFalse((self.root / 'new.py').exists())

    def test_no_newline_on_old_and_new(self):
        (self.root / 'b.py').write_bytes(b'before')
        text = ('diff --git a/b.py b/b.py\nindex 123abcd..456abcd 100644\n'
                '--- a/b.py\n+++ b/b.py\n@@ -1 +1 @@\n-before\n'
                '\\ No newline at end of file\n+after\n\\ No newline at end of file\n')
        self.assertEqual(unified_diff_payload(self.root, ['b.py'], text), {'files': {'b.py': 'after'}})

    def test_repeated_context_is_disambiguated_only_by_coordinates(self):
        (self.root / 'b.py').write_text('same\nsame\nsame\n')
        text = '--- a/b.py\n+++ b/b.py\n@@ -2 +2 @@\n-same\n+changed\n'
        self.assertEqual(unified_diff_payload(self.root, ['b.py'], text)['files']['b.py'],
                         'same\nchanged\nsame\n')
        with self.assertRaises(ValueError):
            unified_diff_payload(self.root, ['b.py'], text.replace('-2 +2', '-8 +8'))

    def test_rejects_overlaps_duplicates_malformed_and_unsupported_changes(self):
        good = self.diff('before\n', 'after\n', 'b.py')
        invalid = [good + good,
                   good + '@@ -1 +1 @@\n-before\n+other\n',
                   good.replace('+1 @@', '+2 @@'),
                   good.replace('-1 +1', '-1,2 +1'),
                   good + 'unrecognized trailer\n',
                   'explanation\n' + good,
                   good.replace('+++ b/b.py', '+++ b/renamed.py'),
                   good.replace('+++ b/b.py', '+++ /dev/null'),
                   'diff --git a/b.py b/b.py\nold mode 100644\nnew mode 100755\n',
                   'diff --git a/b.py b/b.py\nBinary files a/b.py and b/b.py differ\n',
                   'diff --git a/b.py b/b.py\nrename from b.py\nrename to other.py\n',
                   good + 'diff --git a/a.py b/a.py\nindex 123..456 100644\n',
                   good.replace('+after\n', '+after\n\\ No newline at end of file\n+extra\n'),
                   good.replace('+after\n', '+after'),
                   good.replace('--- a/b.py', '--- "a/b.py"'),
                   good.replace('@@ -1 +1 @@', '@@ -1,0 +1,0 @@')]
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                unified_diff_payload(self.root, ['a.py', 'b.py'], text)

    def test_rejects_paths_and_existing_new_file(self):
        (self.root / 'link.py').symlink_to(self.root / 'b.py')
        for name, allowed in [('unknown.py', ['b.py']), ('../escape', ['../escape']),
                              ('/tmp/escape', ['/tmp/escape']), ('link.py', ['link.py']),
                              ('tests/test_x.py', ['tests/test_x.py'])]:
            text = self.diff('before\n', 'after\n', name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                unified_diff_payload(self.root, allowed, text)
        new = '--- /dev/null\n+++ b/b.py\n@@ -0,0 +1 @@\n+overwrite\n'
        with self.assertRaises(ValueError):
            unified_diff_payload(self.root, ['b.py'], new)

    def test_zero_context_insertions_and_deletions(self):
        text = '--- a/b.py\n+++ b/b.py\n@@ -0,0 +1 @@\n+prefix\n@@ -1 +1,0 @@\n-before\n'
        self.assertEqual(unified_diff_payload(self.root, ['b.py'], text), {'files': {'b.py': 'prefix\n'}})

    def test_utf8_crlf_and_timestamp_headers(self):
        (self.root / 'b.py').write_bytes('café\r\n'.encode())
        text = '--- b.py\t2026-01-01\n+++ b.py\t2026-01-02\n@@ -1 +1 @@\n-café\r\n+été\r\n'
        self.assertEqual(unified_diff_payload(self.root, ['b.py'], text), {'files': {'b.py': 'été\r\n'}})

    @unittest.skipUnless(shutil.which('git'), 'git is unavailable for fixture generation')
    def test_actual_git_diff_with_multifile_stale_last_hunk(self):
        # All git writes here are confined to this test's temporary directory.
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True, capture_output=True)
        subprocess.run(['git', 'add', 'a.py', 'b.py'], cwd=self.root, check=True, capture_output=True)
        new = self.old.replace('line 1\n', 'early\n').replace('line 28\n', 'late\n')
        (self.root / 'a.py').write_text(new)
        (self.root / 'b.py').write_text('after\n')
        text = subprocess.run(['git', 'diff', '--no-ext-diff', '--no-color'], cwd=self.root,
                              check=True, capture_output=True, text=True).stdout
        (self.root / 'a.py').write_text(self.old)
        (self.root / 'b.py').write_text('before\n')
        self.assertEqual(unified_diff_payload(self.root, ['a.py', 'b.py'], text),
                         {'files': {'a.py': new, 'b.py': 'after\n'}})
        (self.root / 'b.py').write_text('stale\n')
        with self.assertRaises(ValueError):
            unified_diff_payload(self.root, ['a.py', 'b.py'], text)
        self.assertEqual((self.root / 'a.py').read_text(), self.old)
        self.assertEqual((self.root / 'b.py').read_text(), 'stale\n')
