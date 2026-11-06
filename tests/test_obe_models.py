import unittest
import io
import zipfile
from app.models import QuestionCreate
from app.database import get_db

class TestOBETaggingAndArchive(unittest.TestCase):

    def test_question_create_defaults(self):
        q = QuestionCreate(
            text="Explain LR parsing",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_opt="A",
            pool_id=1
        )
        self.assertEqual(q.difficulty, "MEDIUM")
        self.assertEqual(q.co_tag, "")

    def test_question_create_custom_obe(self):
        q = QuestionCreate(
            text="Construct canonical LR(0) collection",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_opt="A",
            pool_id=2,
            difficulty="HARD",
            co_tag="CO3"
        )
        self.assertEqual(q.difficulty, "HARD")
        self.assertEqual(q.co_tag, "CO3")

    def test_database_records_have_obe_fields(self):
        with get_db() as conn:
            rows = conn.execute("SELECT id, difficulty, co_tag FROM questions LIMIT 5").fetchall()
            for r in rows:
                self.assertIn(r["difficulty"], ["EASY", "MEDIUM", "HARD"])

if __name__ == "__main__":
    unittest.main()
