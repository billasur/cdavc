import tempfile
import unittest
from pathlib import Path

from cdavc.context import ContextIndex, ContextSession


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'a.py').write_text('ordinary line\n' * 800 + 'def tail_symbol(): pass\n')

    def test_tail_relevance_and_retrieval(self):
        index = ContextIndex(self.root, ['a.py'], chunk_chars=1000)
        packed = index.pack('tail_symbol', max_chars=2500)
        self.assertIn('tail_symbol', packed['text'])
        self.assertTrue(packed['omitted'])
        self.assertEqual(packed['used_chars'], len(packed['text']))
        self.assertLessEqual(packed['used_chars'], 2500)
        manifest = index.manifest()
        self.assertEqual(manifest, ContextIndex(self.root, ['a.py'], chunk_chars=1000).manifest())
        self.assertEqual(set(manifest[0]), {'id', 'path', 'start_line', 'end_line', 'sha256', 'chars'})
        self.assertIn('tail_symbol', index.retrieve(manifest[-1]['id']))
        self.assertEqual({x['id'] for x in manifest}, set(packed['included']) | set(packed['omitted']))

    def test_all_budgets(self):
        index = ContextIndex(self.root, ['a.py'])
        for budget in [0, 1, 20, 100, 1000, 20000]:
            packed = index.pack('', max_chars=budget)
            self.assertLessEqual(len(packed['text']), budget)
            self.assertEqual(packed['used_chars'], len(packed['text']))
        with self.assertRaises(ValueError):
            index.pack('', max_chars=-1)

    def test_stale_unknown_and_escaped_chunks(self):
        index = ContextIndex(self.root, ['a.py'])
        chunk = index.manifest()[0]['id']
        (self.root / 'a.py').write_text('changed')
        with self.assertRaises(ValueError):
            index.retrieve(chunk)
        with self.assertRaises(ValueError):
            index.retrieve('../arbitrary')
        for path in ['../escape', '/tmp/escape']:
            with self.assertRaises(ValueError):
                ContextIndex(self.root, [path])
        (self.root / 'link').symlink_to(self.root / 'a.py')
        with self.assertRaises(ValueError):
            ContextIndex(self.root, ['link'])

    def test_session_exposes_search_and_validates_bounded_retrieval(self):
        session = ContextSession(self.root, ['a.py'], query='ordinary', max_chars=2500)
        self.assertLessEqual(len(session.initial()), 2500)
        self.assertIn('context_search', session.initial())
        result = session.respond({'context_search': 'tail_symbol'})
        self.assertIn('tail_symbol', result)
        self.assertLessEqual(len(result), 2500)
        last = session.index.manifest()[-1]['id']
        self.assertIn('tail_symbol', session.respond({'context_requests': [last]}))
        for payload in ({'context_requests': ['unknown']}, {'context_search': '', 'files': {}},
                        {'context_requests': [last, last]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                session.respond(payload)

    def test_smallest_session_budget_exposes_matching_ids_for_followup_retrieval(self):
        (self.root / 'a.py').write_text(('# padding ' + 'x' * 140 + '\n') * 12
                                      + 'def tailneedle(): return 42 # ' + 'y' * 120 + '\n')
        session = ContextSession(self.root, ['a.py'], query='initial', max_chars=512)
        response = session.respond({'context_search': 'tailneedle'})
        matches = [row for row in session.index.manifest() if 'tailneedle' in session.index.retrieve(row['id'])]
        self.assertTrue(matches)
        self.assertIn(matches[0]['id'], response)
        self.assertLessEqual(len(response), 512)
        self.assertIn('tailneedle', session.respond({'context_requests': [matches[0]['id']]}))

    def test_python_chunks_align_to_top_level_definitions(self):
        (self.root / 'b.py').write_text(
            'import os\n'
            '\n'
            '@decorator\n'
            'def alpha(one):\n'
            '    return one\n'
            '\n'
            '# trailing comment\n'
            'class Beta:\n'
            '    def method(self):\n'
            '        pass\n'
        )
        index = ContextIndex(self.root, ['b.py'], chunk_chars=2000)
        manifest = index.manifest()
        self.assertEqual(len(manifest), 3)
        self.assertEqual((manifest[0]['start_line'], manifest[0]['end_line']), (1, 2))
        self.assertEqual((manifest[1]['start_line'], manifest[1]['end_line']), (3, 7))
        self.assertIn('def alpha(one):', index.retrieve(manifest[1]['id']))
        self.assertIn('@decorator', index.retrieve(manifest[1]['id']))
        self.assertEqual((manifest[2]['start_line'], manifest[2]['end_line']), (8, 10))
        self.assertIn('class Beta:', index.retrieve(manifest[2]['id']))
        # A definition name outranks a body mention even when the body is longer.
        ranked = index.ranked('alpha')
        self.assertEqual(ranked[0]['id'], manifest[1]['id'])

    def test_unparseable_python_falls_back_to_character_chunks(self):
        (self.root / 'broken.py').write_text('def broken(:\n    pass\n' * 40)
        index = ContextIndex(self.root, ['broken.py'], chunk_chars=100)
        manifest = index.manifest()
        self.assertGreater(len(manifest), 1)
        for row in manifest:
            self.assertLessEqual(row['chars'], 100)
        self.assertEqual(index.ranked('broken')[0]['id'], manifest[0]['id'])

    def test_oversized_definition_splits_at_line_boundaries(self):
        (self.root / 'big.py').write_text('def huge():\n    body = 1\n' + '    more = 2\n' * 200)
        index = ContextIndex(self.root, ['big.py'], chunk_chars=120)
        manifest = index.manifest()
        self.assertGreater(len(manifest), 2)
        for row in manifest:
            self.assertLessEqual(row['chars'], 120)
        # Every piece of the split definition still ranks for its name.
        self.assertEqual(index.ranked('huge')[0]['id'], manifest[0]['id'])
