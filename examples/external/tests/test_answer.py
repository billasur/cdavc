import unittest

from src.answer import answer


class AnswerTests(unittest.TestCase):
    def test_increment(self):
        self.assertEqual(answer(41), 42)
