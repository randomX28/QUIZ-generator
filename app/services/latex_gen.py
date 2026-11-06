import os
import json
import logging
import subprocess
import tempfile
import shutil
from jinja2 import Environment, FileSystemLoader
from app.config import settings
from app.services.generator import get_paper

logger = logging.getLogger("app.latex_gen")

TEMPLATES_DIR = str(settings.TEMPLATES_DIR)
PDF_CACHE_DIR = str(settings.OUTPUT_DIR)
ROOT_DIR = str(settings.BASE_DIR)
LOGO_FILENAME = settings.LOGO_FILENAME

os.makedirs(PDF_CACHE_DIR, exist_ok=True)


def get_paper_pdf_path(paper_uid: str, bank_id: int | None = None) -> str:
    """Return target path for a single paper PDF inside bank partition (or fallback to root)."""
    if bank_id is not None:
        bank_p = os.path.join(str(settings.get_bank_output_dir(bank_id)), f"{paper_uid}.pdf")
        if os.path.exists(bank_p):
            return bank_p
    # Check legacy flat path
    flat_p = os.path.join(PDF_CACHE_DIR, f"{paper_uid}.pdf")
    if os.path.exists(flat_p):
        return flat_p
    # Destination default
    if bank_id is not None:
        return os.path.join(str(settings.get_bank_output_dir(bank_id)), f"{paper_uid}.pdf")
    return flat_p


def get_bulk_pdf_path(bank_id: int | None = None) -> str:
    """Return target path for bulk bundle PDF."""
    if bank_id is not None:
        bank_p = os.path.join(str(settings.get_bank_output_dir(bank_id)), "all_papers_bundle.pdf")
        if os.path.exists(bank_p):
            return bank_p
    legacy_p = os.path.join(PDF_CACHE_DIR, f"all_papers_bundle{_bank_suffix(bank_id)}.pdf")
    if os.path.exists(legacy_p):
        return legacy_p
    if bank_id is not None:
        return os.path.join(str(settings.get_bank_output_dir(bank_id)), "all_papers_bundle.pdf")
    return legacy_p


def get_answer_keys_pdf_path(bank_id: int | None = None) -> str:
    """Return target path for master answer keys PDF."""
    if bank_id is not None:
        bank_p = os.path.join(str(settings.get_bank_output_dir(bank_id)), "master_answer_keys.pdf")
        if os.path.exists(bank_p):
            return bank_p
    legacy_p = os.path.join(PDF_CACHE_DIR, f"master_answer_keys{_bank_suffix(bank_id)}.pdf")
    if os.path.exists(legacy_p):
        return legacy_p
    if bank_id is not None:
        return os.path.join(str(settings.get_bank_output_dir(bank_id)), "master_answer_keys.pdf")
    return legacy_p


def get_master_paper_pdf_path(bank_id: int | None = 1) -> str:
    """Return target path for master question paper PDF."""
    if bank_id is not None:
        bank_p = os.path.join(str(settings.get_bank_output_dir(bank_id)), "master_question_paper.pdf")
        if os.path.exists(bank_p):
            return bank_p
    legacy_p = os.path.join(PDF_CACHE_DIR, f"master_question_paper{_bank_suffix(bank_id)}.pdf")
    if os.path.exists(legacy_p):
        return legacy_p
    if bank_id is not None:
        return os.path.join(str(settings.get_bank_output_dir(bank_id)), "master_question_paper.pdf")
    return legacy_p


def _prepare_tmp_assets(tmpdir: str):
    """Copy logo and asset files into tmpdir so pdflatex can resolve them."""
    for candidate in [
        os.path.join(ROOT_DIR, LOGO_FILENAME),
        os.path.join(TEMPLATES_DIR, LOGO_FILENAME),
    ]:
        if os.path.isfile(candidate):
            shutil.copy(candidate, os.path.join(tmpdir, LOGO_FILENAME))
            break

# MiKTeX may not be on PATH yet — use full path as fallback
_MIKTEX_BIN = r"C:\Users\nmea\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"


def _find_pdflatex() -> str | None:
    """Return the pdflatex command/path to use, or None if not available."""
    # Try known MiKTeX install location first (full path, avoids PATH issues)
    if os.path.isfile(_MIKTEX_BIN):
        return _MIKTEX_BIN
    # Try system PATH as fallback
    try:
        r = subprocess.run(["pdflatex", "--version"], capture_output=True)
        if r.returncode in (0, 1):   # MiKTeX exits 1 on --version due to update nag
            return "pdflatex"
    except FileNotFoundError:
        pass
    return None


import re

_LATEX_CONV = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\^{}",
    "\\": r"\textbackslash{}",
}
_LATEX_REGEX = re.compile(
    "|".join(re.escape(str(key)) for key in sorted(_LATEX_CONV.keys(), key=lambda item: -len(item)))
)


def tex_escape(text: str) -> str:
    """Escape LaTeX special characters."""
    if text is None:
        return ""
    return _LATEX_REGEX.sub(lambda match: _LATEX_CONV[match.group()], str(text))


def _get_template_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        variable_start_string="<<",
        variable_end_string=">>",
        block_start_string="<%",
        block_end_string="%>",
        comment_start_string="<#",
        comment_end_string="#>",
    )
    env.filters["tex_escape"] = tex_escape
    return env


def render_latex(paper_uid: str) -> str:
    """Render the LaTeX source for a paper."""
    paper = get_paper(paper_uid)
    if not paper:
        raise ValueError(f"Paper '{paper_uid}' not found.")

    env = _get_template_env()
    template = env.get_template("paper.tex.j2")
    return template.render(paper=paper)


def get_or_compile_pdf(paper_uid: str) -> str | None:
    """
    Return path to cached PDF, or compile via pdflatex if available.
    Returns None if pdflatex is not installed.
    """
    paper = get_paper(paper_uid)
    bank_id = paper.get("bank_id") if paper else None
    pdf_path = get_paper_pdf_path(paper_uid, bank_id)

    if os.path.exists(pdf_path):
        return pdf_path

    # Check pdflatex availability
    pdflatex = _find_pdflatex()
    if not pdflatex:
        return None  # pdflatex not available

    latex_source = render_latex(paper_uid)

    with tempfile.TemporaryDirectory() as tmpdir:
        _prepare_tmp_assets(tmpdir)
        tex_file = os.path.join(tmpdir, "paper.tex")
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_source)

        try:
            result = subprocess.run(
                [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", "-output-directory", tmpdir, tex_file],
                capture_output=True, text=True, timeout=15
            )
        except subprocess.TimeoutExpired:
            logger.error(f"pdflatex compilation timed out for paper {paper_uid}")
            return None

        compiled_pdf = os.path.join(tmpdir, "paper.pdf")
        if os.path.exists(compiled_pdf):
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            shutil.copy(compiled_pdf, pdf_path)
            return pdf_path

    return None


def get_latex_source(paper_uid: str) -> str:
    return render_latex(paper_uid)


def _bank_suffix(bank_id) -> str:
    b = _coerce_bank_id(bank_id) if bank_id is not None else None
    return f"_bank{b}" if b and b != 1 else ""


def render_bulk_latex(bank_id: int = None) -> str:
    """Render a combined multi-page LaTeX document containing all generated papers."""
    from app.services.generator import get_all_papers_detailed
    papers = get_all_papers_detailed(bank_id)
    if not papers:
        raise ValueError("No papers found in this bank.")

    env = _get_template_env()
    template = env.get_template("bulk_papers.tex.j2")
    return template.render(papers=papers)


def get_or_compile_bulk_pdf(bank_id: int = None) -> str | None:
    """
    Compile or merge all papers into a single combined multi-page PDF for bulk printing.
    Uses pdflatex if available; otherwise falls back to merging individual cached PDFs via pdfunite/gs.
    """
    pdf_path = get_bulk_pdf_path(bank_id)

    # Fast path: If all individual PDFs exist, stitch via pdfunite (< 1 second)
    try:
        from app.services.generator import get_all_papers_detailed
        papers = get_all_papers_detailed(bank_id)
        pdf_list = [get_paper_pdf_path(p["uid"], p.get("bank_id")) for p in papers]
        if papers and all(os.path.exists(p) for p in pdf_list):
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            r = subprocess.run(["pdfunite"] + pdf_list + [pdf_path], capture_output=True, timeout=15)
            if r.returncode == 0 and os.path.exists(pdf_path):
                return pdf_path
    except Exception as e:
        logger.debug(f"Fast pdfunite stitching bypassed: {e}")

    pdflatex = _find_pdflatex()
    if pdflatex:
        try:
            latex_source = render_bulk_latex(bank_id)
            with tempfile.TemporaryDirectory() as tmpdir:
                _prepare_tmp_assets(tmpdir)
                tex_file = os.path.join(tmpdir, "bulk_papers.tex")
                with open(tex_file, "w", encoding="utf-8") as f:
                    f.write(latex_source)

                subprocess.run(
                    [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", "-output-directory", tmpdir, tex_file],
                    capture_output=True, text=True, timeout=60
                )

                compiled_pdf = os.path.join(tmpdir, "bulk_papers.pdf")
                if os.path.exists(compiled_pdf):
                    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                    shutil.copy(compiled_pdf, pdf_path)
                    return pdf_path
        except Exception as e:
            logger.warning(f"pdflatex bulk compilation failed: {e}")

    # Fallback 1: Merge existing individual paper PDFs if available (using pdfunite or gs)
    try:
        from app.services.generator import get_all_papers_detailed
        papers = get_all_papers_detailed(bank_id)
        pdf_list = []
        for p in papers:
            p_pdf = get_paper_pdf_path(p["uid"], p.get("bank_id"))
            if os.path.exists(p_pdf):
                pdf_list.append(p_pdf)

        if pdf_list:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            # Try pdfunite (standard Poppler CLI)
            r = subprocess.run(["pdfunite"] + pdf_list + [pdf_path], capture_output=True)
            if r.returncode == 0 and os.path.exists(pdf_path):
                return pdf_path

            # Try ghostscript fallback
            gs_cmd = ["gs", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite", f"-sOutputFile={pdf_path}"] + pdf_list
            r_gs = subprocess.run(gs_cmd, capture_output=True)
            if r_gs.returncode == 0 and os.path.exists(pdf_path):
                return pdf_path
    except Exception as e:
        logger.warning(f"PDF merge fallback failed: {e}")

    # Fallback 2: Return existing bundle if already present
    if os.path.exists(pdf_path):
        return pdf_path

    return None



def resolve_paper_answer_keys(paper: dict) -> dict:
    """Helper to resolve correct option letters ('A', 'B', 'C', 'D') for paper questions."""
    keys = {}
    resolved_questions = []
    for q in paper.get("questions", []):
        idx = q["q_index"]
        correct_text = q["correct_opt"].strip().lower()
        correct_label = "A"
        for label, opt_text in q.get("shuffled_options", {}).items():
            if opt_text.strip().lower() == correct_text:
                correct_label = label.upper()
                break
        keys[str(idx)] = correct_label
        rq = dict(q)
        rq["correct_label"] = correct_label
        resolved_questions.append(rq)

    res = dict(paper)
    res["keys"] = keys
    res["questions"] = resolved_questions
    num_q = max(5, len(resolved_questions))
    for i in range(num_q):
        res[f"q{i + 1}"] = keys.get(str(i), "—")
    return res


def render_answer_keys_latex(bank_id: int = None) -> str:
    """Render LaTeX document containing master answer keys for all generated papers."""
    from app.services.generator import get_all_papers_detailed
    papers = get_all_papers_detailed(bank_id)
    if not papers:
        raise ValueError("No papers found in this bank.")

    resolved_papers = [resolve_paper_answer_keys(p) for p in papers]
    meta_paper = papers[-1] if papers else {}
    max_q = max((len(p.get("questions", [])) for p in resolved_papers), default=5)

    env = _get_template_env()
    template = env.get_template("answer_keys.tex.j2")
    return template.render(
        papers=resolved_papers,
        max_q=max_q,
        exam_date=meta_paper.get("exam_date"),
        max_marks=meta_paper.get("max_marks"),
        subject_name=meta_paper.get("subject_name"),
        course_code=meta_paper.get("course_code"),
        exam_title=meta_paper.get("exam_title"),
    )


def get_or_compile_answer_keys_pdf(bank_id: int = None) -> str | None:
    """
    Compile all paper answer keys into a single master answer key PDF for TAs.
    """
    pdf_path = get_answer_keys_pdf_path(bank_id)

    pdflatex = _find_pdflatex()
    if not pdflatex:
        return None

    latex_source = render_answer_keys_latex(bank_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = os.path.join(tmpdir, "answer_keys.tex")
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_source)

        try:
            subprocess.run(
                [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", "-output-directory", tmpdir, tex_file],
                capture_output=True, text=True, timeout=20
            )
        except subprocess.TimeoutExpired:
            logger.error("pdflatex answer keys compilation timed out")
            return None

        compiled_pdf = os.path.join(tmpdir, "answer_keys.pdf")
        if os.path.exists(compiled_pdf):
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            shutil.copy(compiled_pdf, pdf_path)
            return pdf_path

    return None


def _coerce_bank_id(bank_id) -> int:
    if hasattr(bank_id, 'default'):
        bank_id = bank_id.default
    try:
        return int(bank_id) if bank_id is not None else 1
    except (TypeError, ValueError):
        return 1


def render_master_paper_latex(bank_id: int = 1) -> str:
    """Render LaTeX document for the Master Question Paper containing all questions without marked answers."""
    from app.database import get_connection
    from datetime import datetime

    bank_id = _coerce_bank_id(bank_id)
    conn = get_connection()
    bank = conn.execute("SELECT * FROM banks WHERE id=?", (bank_id,)).fetchone()
    rows = conn.execute(
        "SELECT * FROM questions WHERE bank_id=? ORDER BY pool_id, id", (bank_id,)
    ).fetchall()
    conn.close()

    questions = [dict(r) for r in rows]
    subject = (bank["subject_name"] or bank["name"]) if bank else "Compiler Design"
    course = (bank["course_code"] if bank else "") or ""

    env = _get_template_env()
    template = env.get_template("master_paper.tex.j2")
    return template.render(
        questions=questions,
        subject_name=subject,
        course_code=course,
        exam_date=datetime.now().strftime("%d-%b-%Y"),
    )


def get_or_compile_master_paper_pdf(bank_id: int = 1) -> str | None:
    """
    Compile the master question paper into a publication-grade PDF without marked answers.
    """
    pdf_path = get_master_paper_pdf_path(bank_id)

    pdflatex = _find_pdflatex()
    if not pdflatex:
        return None

    latex_source = render_master_paper_latex(bank_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        _prepare_tmp_assets(tmpdir)
        tex_file = os.path.join(tmpdir, "master_question_paper.tex")
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_source)

        try:
            subprocess.run(
                [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", "-output-directory", tmpdir, tex_file],
                capture_output=True, text=True, timeout=20
            )
        except subprocess.TimeoutExpired:
            logger.error("pdflatex answer keys compilation timed out")
            return None

        compiled_pdf = os.path.join(tmpdir, "master_question_paper.pdf")
        if os.path.exists(compiled_pdf):
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            shutil.copy(compiled_pdf, pdf_path)
            return pdf_path

    return None


