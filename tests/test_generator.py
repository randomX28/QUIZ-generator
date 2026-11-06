import unittest
from app.services.generator import _make_uid, _weighted_sample, _shuffle_options

class TestGeneratorService(unittest.TestCase):

    def test_make_uid(self):
        uid = _make_uid(1, "CD")
        self.assertTrue(uid.startswith("CD-"))
        self.assertTrue(uid.endswith("-1"))

        uid_custom = _make_uid(42, "CS302")
        self.assertTrue(uid_custom.startswith("CS302-"))
        self.assertTrue(uid_custom.endswith("-42"))

    def test_weighted_sample_no_duplicates(self):
        questions = [
            {"id": i, "text": f"Question {i}", "times_used": i % 3}
            for i in range(1, 21)
        ]
        sampled = _weighted_sample(questions, k=5, randomize=True)
        self.assertEqual(len(sampled), 5)
        # Check no duplicates
        ids = [q["id"] for q in sampled]
        self.assertEqual(len(ids), len(set(ids)))

    def test_weighted_sample_deterministic(self):
        questions = [
            {"id": 1, "text": "Q1", "times_used": 0},
            {"id": 2, "text": "Q2", "times_used": 1},
            {"id": 3, "text": "Q3", "times_used": 2},
        ]
        sampled = _weighted_sample(questions, k=2, randomize=False)
        self.assertEqual(len(sampled), 2)
        self.assertEqual([q["id"] for q in sampled], [1, 2])

    def test_shuffle_options(self):
        q = {
            "option_a": "Alpha",
            "option_b": "Beta",
            "option_c": "Gamma",
            "option_d": "Delta",
        }
        shuffled = _shuffle_options(q)
        self.assertEqual(set(shuffled.keys()), {"a", "b", "c", "d"})
        self.assertEqual(set(shuffled.values()), {"Alpha", "Beta", "Gamma", "Delta"})

if __name__ == "__main__":
    unittest.main()

