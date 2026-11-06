"""Parse a master LaTeX question paper into individual question records.

Supported layouts:
1. Objective / MCQ questions:
    \\noindent \\textbf{1.} Question text \\hfill \\textbf{[2 Marks]}
    \\begin{tabularx}{\\textwidth}{@{}X X@{}}
    (a) ... & (b) ... \\\\[3pt]
    (c) ... & (d) ... \\\\
    \\end{tabularx}

    Also accepted: "1. text", "\\item text", and \\begin{enumerate}...\\end{enumerate} options.

2. Subjective / Descriptive questions:
    \\noindent \\textbf{1.} Explain LL(1) parsing table construction with an example. \\hfill \\textbf{[5 Marks]}

Correct answers (for MCQs) can be given by any of:
  * a comment inside the question block:   % ans: B
  * a bold option label:                   \\textbf{(b)} ...
  * a trailing "Answer Key" section:       1. B   /   2: C

OBE & Outcome-Based Education metadata (optional):
  * Difficulty:                            % diff: HARD   /   % level: EASY
  * Course Outcome:                        % co: CO2      /   % outcome: CO1
  * Topic:                                 % topic: Lexical Analysis
"""
import random
import re
from typing import List, Dict, Tuple

_START_RE = re.compile(
    r'^[ \t]*(?:\\noindent\s*)?(?:\\textbf\{\s*(\d+)\s*\.\s*\}|(\d+)\s*\.\s+|\\item\b)',
    re.MULTILINE,
)
_OPTS_RE = re.compile(
    r'\\begin\{(tabularx|tabular\*?)\}[^\n]*\n(.*?)\\end\{\1\}'
    r'|\\begin\{enumerate\}(?:\[[^\]]*\])?(.*?)\\end\{enumerate\}',
    re.DOTALL,
)
_MARKS_RE = re.compile(r'\\hfill\s*(?:\\textbf\{)?\s*\[\s*(\d+)\s*(?:marks?)?\s*\]\s*\}?', re.IGNORECASE)
_ANS_COMMENT_RE = re.compile(r'%\s*(?:ans(?:wer)?|correct)\s*[:=]\s*\(?([a-dA-D])\)?', re.IGNORECASE)
_ANS_KEY_LINE_RE = re.compile(r'(\d+)\s*[.:)\-]\s*\(?([A-Da-d])\)?(?![A-Za-z])')

# OBE & metadata regexes
_DIFF_RE = re.compile(r'%\s*(?:diff(?:iculty)?|level)\s*[:=]\s*([a-zA-Z]+)', re.IGNORECASE)
_CO_RE = re.compile(r'%\s*(?:co(?:_tag)?|outcome)\s*[:=]\s*([a-zA-Z0-9_-]+)', re.IGNORECASE)
_TOPIC_RE = re.compile(r'%\s*topic\s*[:=]\s*([^\n\r%]+)', re.IGNORECASE)
_TYPE_FORCE_RE = re.compile(r'%\s*type\s*[:=]\s*(subjective|descriptive|objective|mcq)', re.IGNORECASE)


def _clean_text(s: str) -> str:
    listings = []
    def save_listing(m):
        idx = len(listings)
        listings.append(m.group(0))
        return f"___LSTBLOCK_{idx}___"

    s = re.sub(r'\\begin\{lstlisting\}.*?\\end\{lstlisting\}', save_listing, s, flags=re.DOTALL)

    # Convert \verb into \texttt so it is safe inside tabularx / tabular
    def verb_to_texttt(m):
        c = m.group(2)
        c = c.replace('\\', r'\textbackslash{}')
        c = c.replace('%', r'\%')
        c = c.replace('&', r'\&')
        c = c.replace('_', r'\_')
        return r'\texttt{' + c + '}'

    s = re.sub(r'\\verb(?P<delim>[^\w\s])(.*?)(?P=delim)', verb_to_texttt, s)

    s = re.sub(r'(?<!\\)%.*', '', s)                      # strip comments
    s = re.sub(r'\\vspace\*?\{[^}]*\}', '', s)
    s = re.sub(r'\\noindent', '', s)
    s = re.sub(r'\\{2}(?:\[[^\]]*\])?', ' ', s)          # strip LaTeX row break \\ or \\[3pt]
    s = re.sub(r'[ \t\r\f\v]+', ' ', s)
    s = re.sub(r'\n+', '\n', s)
    s = s.strip()

    for idx, code in enumerate(listings):
        s = s.replace(f"___LSTBLOCK_{idx}___", "\n" + code.strip() + "\n")
    return s.strip()


def _parse_options(content: str) -> Tuple[Dict[str, str], str]:
    """Return ({'a':..,'b':..,'c':..,'d':..}, bold_correct_label_or_empty)."""
    opts, bold = {}, ""
    # Protect \verb|...| constructs from being split on & or \\
    verbs = []
    def save_verb(m):
        idx = len(verbs)
        verbs.append(m.group(0))
        return f"___VERB_{idx}___"

    masked = re.sub(r'\\verb(?P<delim>[^\w\s])(.*?)(?P=delim)', save_verb, content)
    cells = re.split(r'(?<!\\)&|\\{2}(?:\[[^\]]*\])?', masked)
    for cell in cells:
        cell = re.sub(r'(?<!\\)%.*', '', cell).strip()
        for idx, v in enumerate(verbs):
            cell = cell.replace(f"___VERB_{idx}___", v)
        cell = cell.strip()
        m = re.match(r'^(?:\\textbf\{\s*\(([a-dA-D])\)\s*\}|\(([a-dA-D])\))\s*(.*)$', cell, re.DOTALL)
        if not m:
            continue
        label = (m.group(1) or m.group(2)).lower()
        if m.group(1):
            bold = label
        opts[label] = _clean_text(m.group(3))
    return opts, bold


def _parse_enum_options(content: str) -> Dict[str, str]:
    items = [_clean_text(p) for p in re.split(r'\\item', content) if p.strip()]
    opts = {}
    for i, p in enumerate(items):
        if i >= 4:
            break
        label = "abcd"[i]
        p = re.sub(r'^(?:\([a-dA-D]\)|[a-dA-D]\))\s*', '', p)
        opts[label] = p
    return opts


def parse_master_latex(source: str) -> Tuple[List[dict], List[str]]:
    """Return (questions, warnings). Each question has text, options, correct_label, marks, OBE tags, question_type."""
    warnings: List[str] = []
    body = source
    m = re.search(r'\\begin\{document\}(.*?)(?:\\end\{document\}|$)', source, re.DOTALL)
    if m:
        body = m.group(1)

    starts = list(_START_RE.finditer(body))
    # Prefer numbered questions; bare \\item matches (e.g. instruction lists) are noise then
    numbered = [x for x in starts if x.group(1) or x.group(2)]
    if numbered:
        starts = numbered
    if not starts:
        return [], ["No questions found. Expected '1. text' / '\\textbf{1.} text' / '\\item text'."]

    # Answer key section at the tail of the document, if any
    answer_key: Dict[int, str] = {}
    key_pos = re.search(r'answer\s*key|answers', body, re.IGNORECASE)
    key_start = None
    if key_pos and key_pos.start() > starts[-1].start():
        key_start = key_pos.start()
        for n, l in _ANS_KEY_LINE_RE.findall(body[key_start:]):
            answer_key[int(n)] = l.lower()

    questions: List[dict] = []
    for i, st in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(body)
        block = body[st.end():end]
        label = st.group(1) or st.group(2) or str(i + 1)

        # Ignore if block is in the trailing answer key section
        if key_start is not None and st.start() >= key_start:
            continue

        # Extract OBE & metadata comments
        diff = "MEDIUM"
        dm = _DIFF_RE.search(block)
        if dm:
            raw_diff = dm.group(1).upper()
            if raw_diff in ("EASY", "MEDIUM", "HARD"):
                diff = raw_diff

        co_tag = ""
        cm_co = _CO_RE.search(block)
        if cm_co:
            co_tag = cm_co.group(1).upper()

        topic = None
        tm = _TOPIC_RE.search(block)
        if tm:
            topic = tm.group(1).strip()

        # Check for MCQ options block
        opt_match = _OPTS_RE.search(block)

        if not opt_match:
            # ── Support Subjective / Descriptive Question ───────────────
            marks = 5
            q_part = block
            mm = _MARKS_RE.search(q_part)
            if mm:
                marks = int(mm.group(1))
                q_part = _MARKS_RE.sub('', q_part)
            text = _clean_text(q_part)
            if not text:
                warnings.append(f"Q{label}: empty question text — skipped.")
                continue

            questions.append({
                "text": text,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "correct_label": "",
                "marks": marks,
                "question_type": "subjective",
                "difficulty": diff,
                "co_tag": co_tag,
                "topic": topic,
            })
            continue

        # ── Parse Objective / MCQ Question ──────────────────────────────
        if opt_match.group(2) is not None:
            opts, bold = _parse_options(opt_match.group(2))
        else:
            opts, bold = _parse_enum_options(opt_match.group(3)), ""

        if set(opts) != set("abcd") or not all(opts.values()):
            warnings.append(f"Q{label}: could not find all four options (a)-(d) — skipped.")
            continue

        q_part = block[:opt_match.start()]
        marks = 2
        mm = _MARKS_RE.search(q_part)
        if mm:
            marks = int(mm.group(1))
            q_part = _MARKS_RE.sub('', q_part)
        text = _clean_text(q_part)
        if not text:
            warnings.append(f"Q{label}: empty question text — skipped.")
            continue

        correct = bold
        cm = _ANS_COMMENT_RE.search(block)
        if cm:
            correct = cm.group(1).lower()
        if not correct and label.isdigit():
            correct = answer_key.get(int(label), "")

        questions.append({
            "text": text,
            "option_a": opts["a"],
            "option_b": opts["b"],
            "option_c": opts["c"],
            "option_d": opts["d"],
            "correct_label": correct,
            "marks": marks,
            "question_type": "objective",
            "difficulty": diff,
            "co_tag": co_tag,
            "topic": topic,
        })

    return questions, warnings


def distribute_to_pools(questions: List[dict], pool_ids: List[int] = None, pools: int = 5) -> List[dict]:
    """Shuffle and assign pool ids evenly (round-robin) over `pool_ids` (default 1..pools)."""
    targets = list(pool_ids) if pool_ids else list(range(1, pools + 1))
    shuffled = list(questions)
    random.shuffle(shuffled)
    for i, q in enumerate(shuffled):
        q["pool_id"] = targets[i % len(targets)]
    return shuffled


def validate_latex_syntax(latex_code: str) -> List[str]:
    """Lightweight pre-compilation linter to detect common syntax flaws before pdflatex runs."""
    issues = []
    # Strip listings/verbatim before testing math delimiters
    stripped = re.sub(r'\\begin\{lstlisting\}.*?\\end\{lstlisting\}', '', latex_code, flags=re.DOTALL)
    stripped = re.sub(r'\\verb(?P<delim>[^\w\s])(.*?)(?P=delim)', '', stripped)
    # Strip LaTeX comments
    stripped = re.sub(r'(?<!\\)%.*', '', stripped)

    # Check for unclosed environments
    begins = re.findall(r'\\begin\{([a-zA-Z0-9*]+)\}', stripped)
    ends = re.findall(r'\\end\{([a-zA-Z0-9*]+)\}', stripped)
    if len(begins) != len(ends):
        issues.append(f"Unmatched LaTeX environments ({len(begins)} \\begin vs {len(ends)} \\end).")

    # Check inline math $ balance (count unescaped dollar signs)
    dollar_count = len(re.findall(r'(?<!\\)\$', stripped))
    if dollar_count % 2 != 0:
        issues.append("Unbalanced inline math delimiter '$' detected.")

    return issues
