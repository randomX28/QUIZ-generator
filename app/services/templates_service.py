"""Template generation service for LaTeX and Excel question templates."""
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

MASTER_LATEX_TEMPLATE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[top=1.6cm, bottom=1.6cm, left=1.6cm, right=1.6cm]{geometry}
\usepackage{amsmath, amssymb}
\usepackage{tabularx}
\usepackage{array}
\usepackage{listings}

\setlength{\parindent}{0pt}
\pagestyle{plain}

\lstdefinestyle{code}{
  basicstyle=\ttfamily\footnotesize,
  frame=single,
  breaklines=true,
  columns=fullflexible,
  keepspaces=true,
  aboveskip=4pt,
  belowskip=4pt,
  xleftmargin=0.8em
}
\lstset{style=code}

\begin{document}
\footnotesize

\begin{center}
{\large \textbf{Indian Institute of Technology (Indian School of Mines), Dhanbad}}\\[2.5pt]
{\normalsize \textbf{Department of Computer Science and Engineering}}\\[2.5pt]
{\normalsize \textbf{Subject Name (Course Code: CSExxx)}}\\[3pt]
{\large \textbf{MASTER QUESTION PAPER TEMPLATE}}\\[2pt]
\textit{Template Repository --- Import directly into Quiz Generator}\\[4pt]
\end{center}

\noindent
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lll}
\textbf{Subject:} Subject Name & \textbf{Course Code:} CSExxx & \textbf{Date:} DD-Mon-YYYY \\
\textbf{Total Questions:} 5 & \textbf{Format:} Multiple Choice & \textbf{Document:} Master Question Paper \\
\end{tabular*}

\vspace{0.2cm}
\noindent\textbf{Formatting Instructions for Questions:}
\begin{enumerate}\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}
\item Number each question using \texttt{\textbackslash noindent \textbackslash textbf\{1.\}} (or \texttt{1.}).
\item Specify marks at the end of the question text with \texttt{\textbackslash hfill \textbackslash textbf\{[2 Marks]\}}.
\item Place options in a \texttt{tabularx} table with choices \texttt{(a)}, \texttt{(b)}, \texttt{(c)}, and \texttt{(d)}.
\item Indicate the correct answer using a comment \texttt{\% ans: B} right before the options table.
\item Code snippets can be placed inside \texttt{\textbackslash begin\{lstlisting\} ... \textbackslash end\{lstlisting\}}.
\end{enumerate}

\vspace{0.1cm}
\noindent\rule{\textwidth}{0.6pt}
\vspace{0.2cm}

%======================================================================
% SAMPLE QUESTIONS
%======================================================================

\noindent \textbf{1.} Which data structure is typically used by a compiler for symbol table management? \hfill \textbf{[2 Marks]}
% ans: B
\vspace{0.06cm}
\noindent
\begin{tabularx}{\textwidth}{@{}X X@{}}
(a) Stack & (b) Hash Table \\[3pt]
(c) Queue & (d) Linked List \\
\end{tabularx}

\vspace{0.22cm}

\noindent \textbf{2.} Applying standard left recursion elimination to $E \rightarrow E + T \mid T$ yields: \hfill \textbf{[2 Marks]}
% ans: C
\vspace{0.06cm}
\noindent
\begin{tabularx}{\textwidth}{@{}X X@{}}
(a) $E \rightarrow +TE' \mid T$ & (b) $E \rightarrow TE'$, \quad $E' \rightarrow E'+T \mid \epsilon$ \\[3pt]
(c) $E \rightarrow TE'$, \quad $E' \rightarrow +TE' \mid \epsilon$ & (d) $E \rightarrow E'T$, \quad $E' \rightarrow +E' \mid \epsilon$ \\
\end{tabularx}

\vspace{0.22cm}

\noindent \textbf{3.} Consider the following C snippet. What is printed? \hfill \textbf{[2 Marks]}
\begin{lstlisting}
int x = 5;
printf("%d", x++ + ++x);
\end{lstlisting}
% ans: A
\vspace{0.06cm}
\noindent
\begin{tabularx}{\textwidth}{@{}X X@{}}
(a) Undefined behavior & (b) 11 \\[3pt]
(c) 12 & (d) 10 \\
\end{tabularx}

\vspace{0.22cm}

\noindent \textbf{4.} In Lex/Flex, which internal variable contains the length of the currently matched token? \hfill \textbf{[2 Marks]}
% ans: B
\vspace{0.06cm}
\noindent
\begin{tabularx}{\textwidth}{@{}X X@{}}
(a) \texttt{yytext} & (b) \texttt{yyleng} \\[3pt]
(c) \texttt{yylex} & (d) \texttt{yyin} \\
\end{tabularx}

\vspace{0.22cm}

\noindent \textbf{5.} Which parser generator algorithm does Yacc/Bison use? \hfill \textbf{[2 Marks]}
% ans: C
\vspace{0.06cm}
\noindent
\begin{tabularx}{\textwidth}{@{}X X@{}}
(a) LL(1) & (b) LR(0) \\[3pt]
(c) LALR(1) & (d) SLR(1) \\
\end{tabularx}

\vspace{0.3cm}
\noindent\rule{\textwidth}{0.6pt}
\vspace{0.2cm}
\begin{center}
\textit{--- End of Question Paper ---}
\end{center}

\end{document}
"""


def get_master_latex_template() -> str:
    """Return the raw Master LaTeX question paper template string."""
    return MASTER_LATEX_TEMPLATE.strip()


def generate_blank_excel_template() -> io.BytesIO:
    """Download a blank Excel template in LaTeX format with one example sheet per pool."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet

    sheet_names = ["TA_Name_1", "TA_Name_2", "TA_Name_3", "TA_Name_4", "TA_Name_5"]

    example_q = (
        "\\item Let $A=\\{1,2,3\\}$ and $B=\\{a,b\\}$. "
        "The number of functions from $A$ to $B$ is:\n"
        "\\begin{enumerate}[label=(\\Alph*)]\n"
        "    \\item $3$\n"
        "    \\item $5$\n"
        "    \\item $6$\n"
        "    \\item $8$\n"
        "\\end{enumerate}"
    )

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", name="Calibri")

    for name in sheet_names:
        ws = wb.create_sheet(title=name)
        ws.append(["sl no", "question", "solution", "marks"])

        # Style header
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        # One example row
        ws.append([1, example_q, "D", 2])
        ws.row_dimensions[2].height = 120
        ws["B2"].alignment = Alignment(wrap_text=True, vertical="top")
        ws["C2"].alignment = Alignment(horizontal="center", vertical="top")
        ws["D2"].alignment = Alignment(horizontal="center", vertical="top")

        # Column widths
        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 80
        ws.column_dimensions["C"].width = 12
        ws.column_dimensions["D"].width = 10

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

