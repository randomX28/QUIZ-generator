import io
import unittest
from app.services.latex_import import parse_master_latex, distribute_to_pools
from app.database import get_connection

class TestImportEnhancements(unittest.TestCase):

    def test_latex_mixed_objective_and_subjective(self):
        latex = r"""
\documentclass{article}
\begin{document}

\noindent \textbf{1.} What is $2 + 2$? \hfill \textbf{[2 Marks]}
% ans: c
% diff: EASY
% co: CO1
\begin{tabularx}{\textwidth}{@{}X X@{}}
(a) 1 & (b) 2 \\[3pt]
(c) 4 & (d) 5 \\
\end{tabularx}

\noindent \textbf{2.} Explain the role of the lexer and parser in a compiler pipeline. \hfill \textbf{[6 Marks]}
% diff: MEDIUM
% co: CO2
% topic: Front End

\end{document}
"""
        questions, warnings = parse_master_latex(latex)
        self.assertEqual(len(questions), 2)
        self.assertEqual(len(warnings), 0)

        # Q1: Objective
        q1 = questions[0]
        self.assertEqual(q1["question_type"], "objective")
        self.assertEqual(q1["correct_label"], "c")
        self.assertEqual(q1["difficulty"], "EASY")
        self.assertEqual(q1["co_tag"], "CO1")

        # Q2: Subjective
        q2 = questions[1]
        self.assertEqual(q2["question_type"], "subjective")
        self.assertEqual(q2["marks"], 6)
        self.assertEqual(q2["difficulty"], "MEDIUM")
        self.assertEqual(q2["co_tag"], "CO2")
        self.assertEqual(q2["topic"], "Front End")
        self.assertIn("role of the lexer and parser", q2["text"])

    def test_distribute_to_pools_preserves_metadata(self):
        items = [
            {"text": "Q1", "question_type": "objective", "marks": 2, "difficulty": "EASY", "co_tag": "CO1"},
            {"text": "Q2", "question_type": "subjective", "marks": 5, "difficulty": "HARD", "co_tag": "CO3"},
        ]
        distributed = distribute_to_pools(items, pool_ids=[1, 2])
        self.assertEqual(len(distributed), 2)
        self.assertTrue(all("pool_id" in q for q in distributed))
        by_text = {q["text"]: q for q in distributed}
        self.assertEqual(by_text["Q1"]["difficulty"], "EASY")
        self.assertEqual(by_text["Q2"]["difficulty"], "HARD")
        self.assertEqual(by_text["Q1"]["co_tag"], "CO1")
        self.assertEqual(by_text["Q2"]["co_tag"], "CO3")

if __name__ == "__main__":
    unittest.main()
