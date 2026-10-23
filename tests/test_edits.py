import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cdavc.edits import apply_candidate


class EditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'a').write_bytes(b'alpha beta\r\n')

    def test_original_coordinates_and_digest(self):
        digest = hashlib.sha256((self.root / 'a').read_bytes()).hexdigest()
        changed = apply_candidate(self.root, ['a'], {'edits': [
            {'file': 'a', 'find': 'alpha', 'replace': 'beta', 'base_sha256': digest},
            {'file': 'a', 'find': 'beta', 'replace': 'gamma'}]})
        self.assertEqual(changed, ('a',))
        self.assertEqual((self.root / 'a').read_bytes(), b'beta gamma\r\n')

    def test_second_invalid_edit_leaves_original(self):
        with self.assertRaises(ValueError):
            apply_candidate(self.root, ['a'], {'edits': [
                {'file': 'a', 'find': 'alpha', 'replace': 'ok'},
                {'file': 'a', 'find': 'missing', 'replace': 'bad'}]})
        self.assertEqual((self.root / 'a').read_bytes(), b'alpha beta\r\n')

    def test_conflicts_and_invalid_payloads(self):
        cases = [
            {'edits': [{'file': 'a', 'find': 'a', 'replace': ''}]},
            {'edits': [{'file': 'a', 'find': 'alpha', 'replace': ''}, {'file': 'a', 'find': 'pha b', 'replace': ''}]},
            {'files': {'a': 'x'}, 'edits': [{'file': 'a', 'find': 'alpha', 'replace': ''}]},
            {'files': {'a': 'x', 'unknown': 'y'}},
            {'files': {'a': 'x'}, 'edits': None},
            {'edits': [{'file': 'a', 'find': 'alpha', 'replace': '', 'base_sha256': 'wrong'}]},
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                apply_candidate(self.root, ['a'], payload)
            self.assertEqual((self.root / 'a').read_bytes(), b'alpha beta\r\n')

    def test_rollback_restores_bytes_and_removes_new_files(self):
        original = Path.write_bytes
        def fail_last(path, data):
            if path.name == 'z':
                raise OSError('disk failure')
            return original(path, data)
        with patch.object(Path, 'write_bytes', fail_last), self.assertRaises(OSError):
            apply_candidate(self.root, ['a', 'new', 'z'], {'files': {'a': 'changed', 'new': 'new', 'z': 'fail'}})
        self.assertEqual((self.root / 'a').read_bytes(), b'alpha beta\r\n')
        self.assertFalse((self.root / 'new').exists())

    def test_path_escape_and_symlink(self):
        (self.root / 'link').symlink_to(self.root / 'a')
        for path in ['../escape', '/tmp/escape', 'link', './a']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                apply_candidate(self.root, [path], {'files': {path: 'bad'}})
