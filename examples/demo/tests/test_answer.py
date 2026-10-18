import unittest

from src.answer import answer


class AnswerTests(unittest.TestCase):
    def test_answer_increments_value(self):
        self.assertEqual(answer(41), 42)


if __name__ == "__main__":
    unittest.main()
