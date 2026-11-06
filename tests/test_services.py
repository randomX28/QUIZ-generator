import unittest
import openpyxl
from app.services.templates_service import get_master_latex_template, generate_blank_excel_template
from app.services.export_service import export_answer_keys_to_csv, export_answer_keys_to_excel

class TestServices(unittest.TestCase):

    def test_master_latex_template(self):
        tmpl = get_master_latex_template()
        self.assertIn(r"\documentclass", tmpl)
        self.assertIn("MASTER QUESTION PAPER TEMPLATE", tmpl)
        self.assertIn(r"\begin{document}", tmpl)

    def test_generate_blank_excel_template(self):
        buf = generate_blank_excel_template()
        self.assertGreater(buf.getbuffer().nbytes, 0)
        wb = openpyxl.load_workbook(buf)
        self.assertIn("TA_Name_1", wb.sheetnames)
        self.assertEqual(len(wb.sheetnames), 5)

    def test_export_answer_keys_to_csv(self):
        papers = [
            {
                "paper_no": 1,
                "uid": "CD-2026-1",
                "created_at": "2026-03-01",
                "questions": [
                    {
                        "q_index": 0,
                        "shuffled_options": {"a": "opt1", "b": "opt2"},
                        "correct_opt": "opt1",
                    }
                ]
            }
        ]
        buf = export_answer_keys_to_csv(papers)
        content = buf.getvalue().decode("utf-8")
        self.assertIn("CD-2026-1", content)
        self.assertIn("Paper No,Paper Code", content)

    def test_export_answer_keys_to_excel(self):
        papers = [
            {
                "paper_no": 1,
                "uid": "CD-2026-1",
                "created_at": "2026-03-01",
                "questions": [
                    {
                        "q_index": 0,
                        "shuffled_options": {"a": "opt1", "b": "opt2"},
                        "correct_opt": "opt1",
                    }
                ]
            }
        ]
        buf = export_answer_keys_to_excel(papers)
        self.assertGreater(buf.getbuffer().nbytes, 0)
        wb = openpyxl.load_workbook(buf)
        self.assertIn("Master_Answer_Keys", wb.sheetnames)

if __name__ == "__main__":
    unittest.main()

