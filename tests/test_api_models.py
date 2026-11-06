import unittest
from app.models import BankCreate, QuestionCreate

class TestPydanticModels(unittest.TestCase):

    def test_bank_create_model(self):
        b = BankCreate(name="Operating Systems", code="OS", subject_name="OS Lab", course_code="CS303", num_pools=3)
        self.assertEqual(b.name, "Operating Systems")
        self.assertEqual(b.code, "OS")
        self.assertEqual(b.num_pools, 3)

    def test_question_create_model(self):
        q = QuestionCreate(
            text="What is a semaphore?",
            option_a="Variable",
            option_b="Thread",
            option_c="Process",
            option_d="Lock",
            correct_opt="Variable",
            pool_id=1,
            marks=2,
            bank_id=1,
        )
        self.assertEqual(q.correct_opt, "Variable")
        self.assertEqual(q.marks, 2)

if __name__ == "__main__":
    unittest.main()

