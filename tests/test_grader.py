import unittest
from unittest.mock import patch
from app.services.grader import grade_student

class TestGraderService(unittest.TestCase):

    @patch("app.services.grader._save_result")
    @patch("app.services.grader.get_paper")
    def test_grade_student_perfect_score(self, mock_get_paper, mock_save):
        mock_get_paper.return_value = {
            "uid": "CD-2026-1",
            "questions": [
                {
                    "q_index": 0,
                    "text": "What is 2+2?",
                    "shuffled_options": {"a": "3", "b": "4", "c": "5", "d": "6"},
                    "correct_opt": "4",
                    "marks": 2,
                },
                {
                    "q_index": 1,
                    "text": "Capital of France?",
                    "shuffled_options": {"a": "London", "b": "Berlin", "c": "Paris", "d": "Rome"},
                    "correct_opt": "Paris",
                    "marks": 2,
                }
            ]
        }

        # Student answered 'b' for Q0 and 'c' for Q1
        responses = {0: "b", 1: "c"}
        result = grade_student("21JE0001", "CD-2026-1", responses, entered_by="TA")

        self.assertEqual(result["score"], 4)
        self.assertEqual(result["total"], 4)
        self.assertEqual(len(result["breakdown"]), 2)
        self.assertTrue(result["breakdown"][0]["is_correct"])
        self.assertTrue(result["breakdown"][1]["is_correct"])
        mock_save.assert_called_once()

    @patch("app.services.grader._save_result")
    @patch("app.services.grader.get_paper")
    def test_grade_student_partial_score(self, mock_get_paper, mock_save):
        mock_get_paper.return_value = {
            "uid": "CD-2026-1",
            "questions": [
                {
                    "q_index": 0,
                    "text": "What is 2+2?",
                    "shuffled_options": {"a": "3", "b": "4", "c": "5", "d": "6"},
                    "correct_opt": "4",
                    "marks": 2,
                },
                {
                    "q_index": 1,
                    "text": "Capital of France?",
                    "shuffled_options": {"a": "London", "b": "Berlin", "c": "Paris", "d": "Rome"},
                    "correct_opt": "Paris",
                    "marks": 2,
                }
            ]
        }

        # Student answered 'a' (wrong) for Q0 and 'c' (correct) for Q1
        responses = {0: "a", 1: "c"}
        result = grade_student("21JE0002", "CD-2026-1", responses, entered_by="TA")

        self.assertEqual(result["score"], 2)
        self.assertEqual(result["total"], 4)
        self.assertFalse(result["breakdown"][0]["is_correct"])
        self.assertTrue(result["breakdown"][1]["is_correct"])

if __name__ == "__main__":
    unittest.main()

