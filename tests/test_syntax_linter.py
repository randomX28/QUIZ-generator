import unittest
from app.services.latex_import import validate_latex_syntax

class TestLatexSyntaxLinter(unittest.TestCase):

    def test_valid_syntax(self):
        code = r"""
        What is $x + y$?
        \begin{tabularx}{\textwidth}{@{}X X@{}}
        (a) $1$ & (b) $2$ \\
        \end{tabularx}
        """
        issues = validate_latex_syntax(code)
        self.assertEqual(len(issues), 0)

    def test_unbalanced_math_delimiter(self):
        code = "What is $x + y with an unclosed dollar?"
        issues = validate_latex_syntax(code)
        self.assertTrue(any("Unbalanced inline math delimiter" in i for i in issues))

    def test_unmatched_environment(self):
        code = r"""
        \begin{enumerate}
        \item Something
        % Missing \end{enumerate}
        """
        issues = validate_latex_syntax(code)
        self.assertTrue(any("Unmatched LaTeX environments" in i for i in issues))

    def test_escaped_dollar_and_lstlisting_ignored(self):
        code = r"""
        Price is \$50.
        \begin{lstlisting}
        int $x = 10;
        \end{lstlisting}
        What is $2 + 2$?
        """
        issues = validate_latex_syntax(code)
        self.assertEqual(len(issues), 0)

if __name__ == "__main__":
    unittest.main()
