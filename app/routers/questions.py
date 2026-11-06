import openpyxl
import io
import re
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
from typing import List
from app.models import QuestionCreate, QuestionOut
from app.database import get_connection, get_db
from app.services.templates_service import get_master_latex_template, generate_blank_excel_template

router = APIRouter(prefix="/api/questions", tags=["Questions"])

def _ensure_pool(conn, bank_id: int, pool_no: int):
    """Register pool `pool_no` in the bank if it doesn't exist yet."""
    conn.execute(
        "INSERT OR IGNORE INTO pools (bank_id, pool_no, name) VALUES (?, ?, ?)",
        (bank_id, pool_no, f"Pool {pool_no}"),
    )


def _require_bank_and_pool(conn, bank_id: int, pool_no: int):
    if not conn.execute("SELECT 1 FROM banks WHERE id=?", (bank_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Bank not found.")
    if not conn.execute("SELECT 1 FROM pools WHERE bank_id=? AND pool_no=?", (bank_id, pool_no)).fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"Pool {pool_no} does not exist in this bank.")


REQUIRED_COLS = {"question", "option_a", "option_b", "option_c", "option_d", "correct_option", "pool"}
LATEX_REQUIRED_COLS = {"question", "solution"}


@router.get("", response_model=List[QuestionOut])
def list_questions(pool_id: int = None, bank_id: int = None):
    conn = get_connection()
    where, params = [], []
    if bank_id is not None:
        where.append("bank_id=?"); params.append(bank_id)
    if pool_id:
        where.append("pool_id=?"); params.append(pool_id)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(
        f"SELECT * FROM questions {clause} ORDER BY bank_id, pool_id, id", params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("", response_model=QuestionOut, status_code=201)
def create_question(q: QuestionCreate):
    q_type = q.question_type or "objective"
    marks = q.marks if q.marks is not None else (10 if q_type == "subjective" else 2)
    if q_type == "objective":
        options = {q.option_a, q.option_b, q.option_c, q.option_d}
        if q.correct_opt not in options:
            raise HTTPException(
                status_code=400,
                detail="correct_opt must exactly match one of the four option texts."
            )
    conn = get_connection()
    bank_id = q.bank_id or 1
    _require_bank_and_pool(conn, bank_id, q.pool_id)
    cur = conn.execute(
        """INSERT INTO questions (text, option_a, option_b, option_c, option_d,
           correct_opt, pool_id, topic, question_type, marks, bank_id, difficulty, co_tag)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (q.text, q.option_a or "", q.option_b or "", q.option_c or "", q.option_d or "",
         q.correct_opt or "", q.pool_id, q.topic, q_type, marks, bank_id,
         (q.difficulty or "MEDIUM").upper(), (q.co_tag or "").upper())
    )
    new_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM questions WHERE id=?", (new_id,)).fetchone()
    conn.close()
    return dict(row)


@router.put("/{question_id}", response_model=QuestionOut)
def update_question(question_id: int, q: QuestionCreate):
    q_type = q.question_type or "objective"
    marks = q.marks if q.marks is not None else (10 if q_type == "subjective" else 2)
    if q_type == "objective":
        options = {q.option_a, q.option_b, q.option_c, q.option_d}
        if q.correct_opt not in options:
            raise HTTPException(status_code=400, detail="correct_opt must match one of the options.")
    conn = get_connection()
    bank_id = q.bank_id or 1
    _require_bank_and_pool(conn, bank_id, q.pool_id)
    conn.execute(
        """UPDATE questions SET text=?, option_a=?, option_b=?, option_c=?, option_d=?,
           correct_opt=?, pool_id=?, topic=?, question_type=?, marks=?, bank_id=?,
           difficulty=?, co_tag=? WHERE id=?""",
        (q.text, q.option_a or "", q.option_b or "", q.option_c or "", q.option_d or "",
         q.correct_opt or "", q.pool_id, q.topic, q_type, marks, bank_id,
         (q.difficulty or "MEDIUM").upper(), (q.co_tag or "").upper(), question_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found.")
    return dict(row)


@router.delete("/clear", status_code=200)
@router.post("/clear", status_code=200)
@router.delete("", status_code=200)
def clear_questions(pool_id: int = None, bank_id: int = None):
    conn = get_connection()
    where, params = [], []
    if bank_id is not None:
        where.append("bank_id=?"); params.append(bank_id)
    if pool_id is not None:
        where.append("pool_id=?"); params.append(pool_id)
    if where:
        cur = conn.execute("DELETE FROM questions WHERE " + " AND ".join(where), params)
        deleted = cur.rowcount
    else:
        cur = conn.execute("DELETE FROM questions")
        deleted = cur.rowcount
        conn.execute("DELETE FROM sqlite_sequence WHERE name='questions'")
    conn.commit()
    conn.close()
    return {"deleted": deleted, "message": f"Successfully cleared {deleted} question(s)."}


@router.delete("/{question_id}", status_code=204)
def delete_question(question_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM questions WHERE id=?", (question_id,))
    conn.commit()
    conn.close()


@router.get("/stats")
def pool_stats(bank_id: int = 1):
    conn = get_connection()
    rows = conn.execute(
        "SELECT pool_id, COUNT(*) as count, SUM(times_used) as total_uses FROM questions WHERE bank_id=? GROUP BY pool_id",
        (bank_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── LaTeX Question Parser ──────────────────────────────────────────────────

# Aliases: map variant column names to the canonical name we check for
HEADER_ALIASES = {
    "answer":    "solution",   # 'Answer' column = answer letter
    "ans":       "solution",
    "sl":        "sl no",
    "s.no":      "sl no",
    "sno":       "sl no",
    "serial":    "sl no",
    "sl.no":     "sl no",
    "diff":      "difficulty",
    "level":     "difficulty",
    "co":        "co_tag",
    "outcome":   "co_tag",
    "cotag":     "co_tag",
    "type":      "question_type",
    "qtype":     "question_type",
}


def normalise_headers(raw_headers: list) -> dict:
    """Return header_map with canonical names (aliases resolved)."""
    mapping = {}
    for i, h in enumerate(raw_headers):
        canonical = HEADER_ALIASES.get(h, h)   # resolve alias or keep as-is
        if canonical not in mapping:            # first occurrence wins
            mapping[canonical] = i
    return mapping


def parse_latex_question(cell_text: str):
    """
    Parse a LaTeX-formatted question cell.  Handles both single-line and
    multi-line cells, and \\begin{enumerate} with or without [label=...] option.

    Example (single-line, real format):
        \\item Question text? \\begin{enumerate} \\item $2$ \\item $3$ \\item $4$ \\item $5$ \\end{enumerate}

    Returns: (question_text, opt_a, opt_b, opt_c, opt_d)
    Raises ValueError with a descriptive message on parse failure.
    """
    text = str(cell_text).strip()

    # Find the enumerate block (lazy, works on single or multi-line)
    enum_match = re.search(
        r'\\begin\{enumerate\}.*?\\end\{enumerate\}',
        text, re.DOTALL
    )
    if not enum_match:
        raise ValueError("No \\begin{enumerate}...\\end{enumerate} block found")

    enum_block  = enum_match.group(0)
    before_enum = text[:enum_match.start()].strip()

    # Strip leading \item from question text
    question_text = re.sub(r'^\\item\s*', '', before_enum).strip()
    if not question_text:
        raise ValueError("Question text is empty before the enumerate block")

    # Extract inner content — skip optional [label=...] argument after \begin{enumerate}
    # Works whether content is on one line or multiple lines
    inner_match = re.search(
        r'\\begin\{enumerate\}(?:\[[^\]]*\])?\s*(.*?)\\end\{enumerate\}',
        enum_block, re.DOTALL
    )
    if not inner_match:
        raise ValueError("Could not parse inside enumerate block")

    items_raw = re.split(r'\\item', inner_match.group(1))
    options   = [p.strip() for p in items_raw if p.strip()]

    if len(options) < 4:
        raise ValueError(f"Expected 4 options inside enumerate, found {len(options)}")

    return question_text, options[0], options[1], options[2], options[3]


# ── Bulk Excel Import (LaTeX multi-sheet format) ───────────────────────────

@router.post("/import", status_code=201)
async def import_from_excel(
    file: UploadFile = File(...),
    bank_id: int = Form(1),
    preview: bool = Form(False),
    on_duplicate: str = Form("skip"),
):
    """
    Upload an .xlsx/.xls file to bulk-import questions.
    Supports preview dry-run and on_duplicate ('skip' vs 'overwrite').
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx / .xls files are accepted.")

    content = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read Excel file: {e}")

    conn = get_connection()
    if not conn.execute("SELECT 1 FROM banks WHERE id=?", (bank_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Bank not found.")

    # Fetch existing question texts (in this bank) for duplicate check
    existing_texts = {
        row[0].strip().lower()
        for row in conn.execute("SELECT text FROM questions WHERE bank_id=?", (bank_id,)).fetchall()
    }

    sheet_results = []
    staged_questions = []
    total_inserted = 0
    total_skipped  = 0
    total_dup      = 0

    for sheet_idx, ws in enumerate(wb.worksheets):
        pool_id   = sheet_idx + 1
        ta_name   = ws.title
        rows      = list(ws.iter_rows(values_only=True))

        if not rows:
            sheet_results.append({"sheet": ta_name, "pool": pool_id,
                                   "imported": 0, "skipped": 0, "duplicates": 0,
                                   "errors": ["Sheet is empty"]})
            continue

        raw_headers = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
        header_map  = normalise_headers(raw_headers)
        col_set     = set(header_map.keys()) - {""}

        is_latex  = LATEX_REQUIRED_COLS.issubset(col_set) and "option_a" not in col_set
        is_legacy = REQUIRED_COLS.issubset(col_set)

        if not is_latex and not is_legacy:
            missing_latex  = LATEX_REQUIRED_COLS  - col_set
            missing_legacy = REQUIRED_COLS - col_set
            sheet_results.append({
                "sheet":  ta_name,
                "pool":   pool_id,
                "imported": 0, "skipped": 0, "duplicates": 0,
                "errors": [
                    f"Unrecognised column layout. "
                    f"For LaTeX format missing: {sorted(missing_latex)}. "
                    f"For legacy format missing: {sorted(missing_legacy)}. "
                    f"Found: {sorted(col_set)}"
                ]
            })
            continue

        def get_cell(row, name, default=None):
            idx = header_map.get(name)
            if idx is None or idx >= len(row):
                return default
            val = row[idx]
            return str(val).strip() if val is not None else default

        inserted, skipped_err, duplicates = 0, 0, 0
        errors = []

        for row_i, row in enumerate(rows[1:], start=2):
            if all(v is None for v in row):
                continue

            if is_latex:
                q_cell  = get_cell(row, "question")
                sol_raw = (get_cell(row, "solution") or "").strip().upper()

                if not q_cell:
                    errors.append({"row": row_i, "errors": ["question cell is empty"]})
                    skipped_err += 1
                    continue

                try:
                    q_text, opt_a, opt_b, opt_c, opt_d = parse_latex_question(q_cell)
                except ValueError as e:
                    errors.append({"row": row_i, "errors": [str(e)]})
                    skipped_err += 1
                    continue

                label_map = {"A": opt_a, "B": opt_b, "C": opt_c, "D": opt_d}
                if sol_raw not in label_map:
                    errors.append({"row": row_i,
                                   "errors": [f"solution '{sol_raw}' must be A/B/C/D"]})
                    skipped_err += 1
                    continue

                correct_opt = label_map[sol_raw]
                topic       = get_cell(row, "topic", None)
                q_type      = "objective"

            else:
                q_text    = get_cell(row, "question")
                opt_a     = get_cell(row, "option_a", "")
                opt_b     = get_cell(row, "option_b", "")
                opt_c     = get_cell(row, "option_c", "")
                opt_d     = get_cell(row, "option_d", "")
                correct_l = (get_cell(row, "correct_option") or "").lower().strip()
                pool_raw  = get_cell(row, "pool")
                topic     = get_cell(row, "topic", None)
                q_type    = (get_cell(row, "question_type") or "objective").strip().lower()

                row_errors = []
                if not q_text: row_errors.append("question is empty")
                if q_type == "objective":
                    if not opt_a:  row_errors.append("option_a is empty")
                    if not opt_b:  row_errors.append("option_b is empty")
                    if not opt_c:  row_errors.append("option_c is empty")
                    if not opt_d:  row_errors.append("option_d is empty")
                    if correct_l not in ("a", "b", "c", "d"):
                        row_errors.append(f"correct_option '{correct_l}' must be a/b/c/d")

                try:
                    pool_id = int(float(pool_raw)) if pool_raw else pool_id
                    if pool_id < 1:
                        row_errors.append(f"pool '{pool_raw}' must be 1 or greater")
                except (TypeError, ValueError):
                    row_errors.append(f"pool '{pool_raw}' is not a valid number")

                if row_errors:
                    errors.append({"row": row_i, "errors": row_errors})
                    skipped_err += 1
                    continue

                label_map   = {"a": opt_a, "b": opt_b, "c": opt_c, "d": opt_d}
                correct_opt = label_map.get(correct_l, "")

            q_marks = 2
            if "marks" in header_map:
                try:
                    raw_m = row[header_map["marks"]]
                    if raw_m is not None and str(raw_m).strip():
                        q_marks = int(float(str(raw_m).strip()))
                except (ValueError, TypeError):
                    q_marks = 2

            diff_raw = (get_cell(row, "difficulty") or "MEDIUM").strip().upper()
            q_diff = diff_raw if diff_raw in ("EASY", "MEDIUM", "HARD") else "MEDIUM"
            q_co = (get_cell(row, "co_tag") or "").strip().upper()

            is_dup = q_text.strip().lower() in existing_texts
            if is_dup:
                duplicates += 1

            if preview:
                staged_questions.append({
                    "text": q_text,
                    "option_a": opt_a, "option_b": opt_b, "option_c": opt_c, "option_d": opt_d,
                    "correct_opt": correct_opt,
                    "pool_id": pool_id,
                    "topic": topic,
                    "marks": q_marks,
                    "difficulty": q_diff,
                    "co_tag": q_co,
                    "question_type": q_type,
                    "is_duplicate": is_dup,
                    "sheet": ta_name,
                })
                inserted += 1
                continue

            # In commit mode
            if is_dup:
                if on_duplicate == "overwrite":
                    conn.execute(
                        """UPDATE questions
                           SET option_a=?, option_b=?, option_c=?, option_d=?,
                               correct_opt=?, pool_id=?, topic=?, marks=?,
                               difficulty=?, co_tag=?, question_type=?
                           WHERE bank_id=? AND LOWER(TRIM(text))=?""",
                        (opt_a, opt_b, opt_c, opt_d, correct_opt, pool_id, topic, q_marks,
                         q_diff, q_co, q_type, bank_id, q_text.strip().lower())
                    )
                    inserted += 1
                continue

            _ensure_pool(conn, bank_id, pool_id)
            conn.execute(
                """INSERT INTO questions
                       (text, option_a, option_b, option_c, option_d,
                        correct_opt, pool_id, topic, marks, bank_id, difficulty, co_tag, question_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (q_text, opt_a, opt_b, opt_c, opt_d, correct_opt, pool_id, topic, q_marks, bank_id, q_diff, q_co, q_type)
            )
            existing_texts.add(q_text.strip().lower())
            inserted += 1

        if not preview:
            conn.commit()

        sheet_results.append({
            "sheet":      ta_name,
            "pool":       pool_id,
            "imported":   inserted,
            "skipped":    skipped_err,
            "duplicates": duplicates,
            "errors":     errors[:20],
        })
        total_inserted += inserted
        total_skipped  += skipped_err
        total_dup      += duplicates

    conn.close()

    if preview:
        return {
            "preview": True,
            "total_found": len(staged_questions),
            "duplicates": total_dup,
            "objective_count": sum(1 for q in staged_questions if q.get("question_type") == "objective"),
            "subjective_count": sum(1 for q in staged_questions if q.get("question_type") == "subjective"),
            "missing_answers": sum(1 for q in staged_questions if q.get("question_type") == "objective" and not q.get("correct_opt")),
            "sheets": sheet_results,
            "questions": staged_questions[:150],
        }

    return {
        "total_imported":   total_inserted,
        "total_skipped":    total_skipped,
        "total_duplicates": total_dup,
        "sheets":           sheet_results,
    }


# ── Master LaTeX import ───────────────────────────────────────────────────

@router.post("/import-latex", status_code=201)
async def import_from_latex(
    file: UploadFile = File(...),
    bank_id: int = Form(1),
    pool_ids: str = Form(""),
    new_pools: int = Form(0),
    preview: bool = Form(False),
    on_duplicate: str = Form("skip"),
):
    """
    Upload a master LaTeX (.tex) question paper.
    Supports preview dry-run, subjective questions, OBE tags, and conflict resolution ('skip'/'overwrite').
    """
    from app.services.latex_import import parse_master_latex, distribute_to_pools

    if not (file.filename or "").lower().endswith((".tex", ".txt")):
        raise HTTPException(status_code=400, detail="Only .tex files are accepted.")

    raw = await file.read()
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        source = raw.decode("latin-1")

    parsed, warnings = parse_master_latex(source)
    if not parsed:
        raise HTTPException(status_code=400, detail=" ".join(warnings) or "No questions found.")

    conn = get_connection()
    if not conn.execute("SELECT 1 FROM banks WHERE id=?", (bank_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Bank not found.")
    existing = {r[0].strip().lower() for r in conn.execute(
        "SELECT text FROM questions WHERE bank_id=?", (bank_id,)).fetchall()}

    # Resolve target pools
    bank_pools = [r[0] for r in conn.execute(
        "SELECT pool_no FROM pools WHERE bank_id=? ORDER BY pool_no", (bank_id,)).fetchall()]
    try:
        chosen = [int(x) for x in pool_ids.split(",") if x.strip()]
    except ValueError:
        conn.close()
        raise HTTPException(status_code=400, detail="pool_ids must be comma-separated pool numbers.")
    bad = [p for p in chosen if p not in bank_pools]
    if bad:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Pool(s) {bad} do not exist in this bank.")
    targets = list(chosen)
    if not preview:
        for _ in range(max(0, min(new_pools, 100))):
            nxt = conn.execute("SELECT COALESCE(MAX(pool_no),0)+1 FROM pools WHERE bank_id=?", (bank_id,)).fetchone()[0]
            _ensure_pool(conn, bank_id, nxt)
            targets.append(nxt)
    else:
        # Simulate new pools in preview
        max_p = max(bank_pools) if bank_pools else 0
        for i in range(1, max(0, min(new_pools, 100)) + 1):
            targets.append(max_p + i)

    if not targets:
        targets = bank_pools
    if not targets:
        if not preview:
            for n in range(1, 6):
                _ensure_pool(conn, bank_id, n)
        targets = [1, 2, 3, 4, 5]
    targets = sorted(set(targets))

    distributed = distribute_to_pools(parsed, pool_ids=targets)

    if preview:
        conn.close()
        dup_count = sum(1 for q in distributed if q["text"].strip().lower() in existing)
        missing_count = sum(1 for q in distributed if q.get("question_type") == "objective" and not q.get("correct_label"))
        return {
            "preview": True,
            "total_found": len(distributed),
            "duplicates": dup_count,
            "objective_count": sum(1 for q in distributed if q.get("question_type") == "objective"),
            "subjective_count": sum(1 for q in distributed if q.get("question_type") == "subjective"),
            "missing_answers": missing_count,
            "warnings": warnings,
            "questions": [
                {
                    **q,
                    "is_duplicate": q["text"].strip().lower() in existing,
                }
                for q in distributed
            ],
            "per_pool": {p: sum(1 for q in distributed if q.get("pool_id") == p) for p in targets},
        }

    # Commit Mode
    inserted = 0
    duplicates = 0
    per_pool = {p: 0 for p in targets}
    no_answer = 0

    for q in distributed:
        key = q["text"].strip().lower()
        is_dup = key in existing
        q_type = q.get("question_type", "objective")
        correct = ""

        if q_type == "objective":
            opts = {"a": q["option_a"], "b": q["option_b"], "c": q["option_c"], "d": q["option_d"]}
            correct = opts.get(q["correct_label"], "")
            if not correct:
                no_answer += 1

        if is_dup:
            if on_duplicate == "overwrite":
                conn.execute(
                    """UPDATE questions
                       SET option_a=?, option_b=?, option_c=?, option_d=?,
                           correct_opt=?, pool_id=?, topic=?, question_type=?, marks=?,
                           difficulty=?, co_tag=?
                       WHERE bank_id=? AND LOWER(TRIM(text))=?""",
                    (q["option_a"], q["option_b"], q["option_c"], q["option_d"],
                     correct, q["pool_id"], q.get("topic"), q_type,
                     q["marks"], q.get("difficulty", "MEDIUM"), q.get("co_tag", ""),
                     bank_id, key)
                )
                inserted += 1
                per_pool[q["pool_id"]] += 1
            else:
                duplicates += 1
            continue

        conn.execute(
            """INSERT INTO questions (text, option_a, option_b, option_c, option_d,
                   correct_opt, pool_id, topic, question_type, marks, bank_id, difficulty, co_tag)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (q["text"], q["option_a"], q["option_b"], q["option_c"], q["option_d"],
             correct, q["pool_id"], q.get("topic"), q_type,
             q["marks"], bank_id, q.get("difficulty", "MEDIUM"), q.get("co_tag", ""))
        )
        existing.add(key)
        inserted += 1
        per_pool[q["pool_id"]] += 1

    conn.commit()
    conn.close()

    if no_answer:
        warnings.append(
            f"{no_answer} imported question(s) have NO correct answer set (grading will mark them wrong). "
            "Mark answers in the file (e.g. '% ans: B' or an Answer Key section) or edit them in the Question Bank."
        )

    return {
        "total_found": len(distributed),
        "imported": inserted,
        "duplicates": duplicates,
        "missing_answers": no_answer,
        "per_pool": per_pool,
        "warnings": warnings,
    }


# ── Download blank template (LaTeX format) ────────────────────────────────

@router.get("/template")
def download_template():
    """Download a blank Excel template in LaTeX format with one example sheet per pool."""
    buf = generate_blank_excel_template()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=questions_template.xlsx"}
    )


# ── Download blank master LaTeX template ───────────────────────────────────

@router.get("/template/latex")
def download_latex_template():
    """Download a ready-to-use Master LaTeX question paper template (.tex)."""
    return Response(
        content=get_master_latex_template(),
        media_type="application/x-tex",
        headers={"Content-Disposition": "attachment; filename=master_questions_template.tex"}
    )


# ── Standalone Question Bank Export (Zip Archive) ──────────────────────────

@router.get("/export/archive")
def export_questions_archive(bank_id: int = 1):
    """Export complete question bank as a .zip bundle containing both Excel and LaTeX master."""
    import zipfile
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from app.services.latex_gen import render_master_paper_latex

    conn = get_connection()
    bank_row = conn.execute("SELECT * FROM banks WHERE id=?", (bank_id,)).fetchone()
    q_rows = conn.execute(
        "SELECT * FROM questions WHERE bank_id=? ORDER BY pool_id, id", (bank_id,)
    ).fetchall()
    conn.close()

    bank_code = bank_row["code"] if bank_row else f"bank{bank_id}"

    # 1. Build Excel Catalog
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Question_Bank"

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    headers = ["ID", "Pool", "Question Text", "Option A", "Option B", "Option C", "Option D",
               "Correct Answer", "Type", "Marks", "Difficulty", "CO Tag", "Times Used"]
    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in q_rows:
        ws.append([
            r["id"], r["pool_id"], r["text"], r["option_a"], r["option_b"],
            r["option_c"], r["option_d"], r["correct_opt"], r["question_type"],
            r["marks"], r["difficulty"] or "MEDIUM", r["co_tag"] or "", r["times_used"]
        ])

    excel_buf = io.BytesIO()
    wb.save(excel_buf)
    excel_buf.seek(0)

    # 2. Build LaTeX Master
    try:
        latex_content = render_master_paper_latex(bank_id)
    except Exception:
        latex_content = "% LaTeX generation unavailable"

    # 3. Assemble Zip
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"questions_{bank_code}.xlsx", excel_buf.getvalue())
        zf.writestr(f"master_paper_{bank_code}.tex", latex_content)

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="question_bank_{bank_code}_archive.zip"'}
    )

