import unittest
from app.services.latex_import import parse_master_latex, _clean_text, _parse_options

class TestLatexImport(unittest.TestCase):

    def test_clean_text_verb_to_texttt(self):
        raw = r"Look at \verb|[+-*/%]| and \verb|test_var| here."
        cleaned = _clean_text(raw)
        self.assertIn(r"\texttt{[+-*/\%]}", cleaned)
        self.assertIn(r"\texttt{test\_var}", cleaned)

    def test_clean_text_preserves_lstlisting(self):
        raw = (
            "Consider the snippet:\n"
            "\\begin{lstlisting}\n"
            "int x = 10;\n"
            "printf(\"%d\", x);\n"
            "\\end{lstlisting}\n"
            "What does it print?"
        )
        cleaned = _clean_text(raw)
        self.assertIn("int x = 10;", cleaned)
        self.assertIn(r'\begin{lstlisting}', cleaned)
        self.assertIn(r'\end{lstlisting}', cleaned)

    def test_parse_options_tabularx(self):
        content = (
            r"(a) First option & (b) Second option \\" "\n"
            r"(c) Third option & (d) Fourth option \\"
        )
        opts, bold = _parse_options(content)
        self.assertEqual(opts["a"], "First option")
        self.assertEqual(opts["b"], "Second option")
        self.assertEqual(opts["c"], "Third option")
        self.assertEqual(opts["d"], "Fourth option")
        self.assertEqual(bold, "")

    def test_parse_options_with_bold_label(self):
        content = (
            r"(a) Alpha & \textbf{(b)} Beta \\" "\n"
            r"(c) Gamma & (d) Delta \\"
        )
        opts, bold = _parse_options(content)
        self.assertEqual(bold, "b")
        self.assertEqual(opts["b"], "Beta")

    def test_parse_master_latex_with_comment_answers(self):
        latex = r"""
\documentclass{article}
\begin{document}

\noindent \textbf{1.} What is $1 + 1$? \hfill \textbf{[2 Marks]}
% ans: b
\begin{tabularx}{\textwidth}{@{}X X@{}}
(a) 1 & (b) 2 \\[3pt]
(c) 3 & (d) 4 \\
\end{tabularx}

\noindent \textbf{2.} Which of these is a keyword? \hfill \textbf{[2 Marks]}
% ans: a
\begin{tabularx}{\textwidth}{@{}X X@{}}
(a) \texttt{while} & (b) \texttt{variable} \\[3pt]
(c) \texttt{constant} & (d) \texttt{number} \\
\end{tabularx}

\end{document}
"""
        questions, warnings = parse_master_latex(latex)
        self.assertEqual(len(questions), 2)
        self.assertEqual(len(warnings), 0)

        q1 = questions[0]
        self.assertIn("$1 + 1$", q1["text"])
        self.assertEqual(q1["option_a"], "1")
        self.assertEqual(q1["option_b"], "2")
        self.assertEqual(q1["correct_label"], "b")
        self.assertEqual(q1["marks"], 2)

        q2 = questions[1]
        self.assertIn("Which of these is a keyword?", q2["text"])
        self.assertEqual(q2["correct_label"], "a")

    def test_parse_master_latex_subjective_and_obe(self):
        latex = r"""
\documentclass{article}
\begin{document}

\noindent \textbf{1.} Construct the LL(1) parsing table for $E \to E + T \mid T$. \hfill \textbf{[5 Marks]}
% diff: HARD
% co: CO2
% topic: Syntax Analysis

\noindent \textbf{2.} What is lexical analysis? \hfill \textbf{[3 Marks]}
% diff: EASY
% co: CO1

\end{document}
"""
        questions, warnings = parse_master_latex(latex)
        self.assertEqual(len(questions), 2)
        self.assertEqual(len(warnings), 0)

        q1 = questions[0]
        self.assertEqual(q1["question_type"], "subjective")
        self.assertEqual(q1["marks"], 5)
        self.assertEqual(q1["difficulty"], "HARD")
        self.assertEqual(q1["co_tag"], "CO2")
        self.assertEqual(q1["topic"], "Syntax Analysis")
        self.assertIn("Construct the LL(1) parsing table", q1["text"])

        q2 = questions[1]
        self.assertEqual(q2["question_type"], "subjective")
        self.assertEqual(q2["marks"], 3)
        self.assertEqual(q2["difficulty"], "EASY")
        self.assertEqual(q2["co_tag"], "CO1")

if __name__ == "__main__":
    unittest.main()
