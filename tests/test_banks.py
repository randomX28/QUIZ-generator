import unittest
from app.config import settings

class TestBankConfiguration(unittest.TestCase):

    def test_settings_paths(self):
        self.assertTrue(str(settings.BASE_DIR).endswith("QUIZ generator"))
        self.assertTrue(str(settings.OUTPUT_DIR).endswith("generated_papers"))
        self.assertTrue(str(settings.DB_PATH).endswith("quiz.db"))

    def test_bank_output_dir(self):
        dir_1 = settings.get_bank_output_dir(1)
        dir_21 = settings.get_bank_output_dir(21)
        self.assertTrue(str(dir_1).endswith("bank_1"))
        self.assertTrue(str(dir_21).endswith("bank_21"))
        self.assertTrue(dir_1.exists())
        self.assertTrue(dir_21.exists())

if __name__ == "__main__":
    unittest.main()

