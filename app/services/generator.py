import random
import json
from datetime import datetime
from typing import List, Set
from app.database import get_connection


def _make_uid(paper_no: int, code: str = "CD") -> str:
    """Build a clean, sequential UID: <BANKCODE>-YYYY-N (e.g. CD-2026-1)"""
    return f"{code}-{datetime.now().year}-{paper_no}"


def get_bank(bank_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM banks WHERE id=?", (bank_id,)).fetchone()
    conn.close()
    return dict(row) if row else None



def _weighted_choice(questions: List[dict]) -> dict:
    """
    Weighted random: questions with fewer uses are more likely to be picked.
    Weight = 1 / (times_used + 1)  so unused questions have weight 1, used ones less.
    """
    if not questions:
        raise ValueError("Pool is empty — add questions before generating papers.")
    weights = [1.0 / (q["times_used"] + 1) for q in questions]
    return random.choices(questions, weights=weights, k=1)[0]


def _weighted_sample(questions: List[dict], k: int, randomize: bool = True) -> List[dict]:
    """
    Pick `k` distinct questions from `questions` without replacement.
    In randomized mode, uses weighted random choice (least-used preferred).
    In deterministic mode, takes the first `k` questions (already ordered by times_used ASC).
    """
    if k <= 0:
        return []
    if k >= len(questions):
        picked = list(questions)
        if randomize:
            random.shuffle(picked)
        return picked
    if not randomize:
        return list(questions[:k])

    remaining = list(questions)
    picked = []
    for _ in range(k):
        chosen = _weighted_choice(remaining)
        picked.append(chosen)
        remaining = [q for q in remaining if q["id"] != chosen["id"]]
    return picked


def _shuffle_options(question: dict) -> dict:
    """Return options dict with shuffled labels preserving text."""
    options = [
        question["option_a"],
        question["option_b"],
        question["option_c"],
        question["option_d"],
    ]
    random.shuffle(options)
    return {"a": options[0], "b": options[1], "c": options[2], "d": options[3]}


def _increment_times_used(question_ids: List[int]):
    conn = get_connection()
    conn.executemany(
        "UPDATE questions SET times_used = times_used + 1 WHERE id = ?",
        [(qid,) for qid in question_ids]
    )
    conn.commit()
    conn.close()


from app.models import (
    DEFAULT_SUBJECT_NAME,
    DEFAULT_COURSE_CODE,
    DEFAULT_QUIZ_TITLE,
    DEFAULT_SEMESTER_TITLE,
    DEFAULT_QUIZ_MARKS,
    DEFAULT_SEMESTER_MARKS,
    DEFAULT_QUIZ_DURATION,
    DEFAULT_SEMESTER_DURATION,
    DEFAULT_QUIZ_INSTRUCTIONS,
    DEFAULT_SEMESTER_INSTRUCTIONS,
    DEFAULT_DURATION,
    DEFAULT_INSTRUCTIONS,
)


def _next_paper_no(bank_id: int = 1) -> int:
    """Return the next sequential paper number for a bank (MAX + 1, starting at 1)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(MAX(paper_no), 0) FROM papers WHERE bank_id = ?", (bank_id,)
    ).fetchone()
    conn.close()
    return row[0] + 1


def _uid_exists(uid: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM papers WHERE uid = ?", (uid,)).fetchone()
    conn.close()
    return row is not None


def _get_pool_questions(bank_id: int, pool_id: int, question_type: str = "objective") -> List[dict]:
    conn = get_connection()
    # If subjective requested, check if dedicated subjective questions exist in this pool
    if question_type == "subjective":
        rows = conn.execute(
            "SELECT * FROM questions WHERE bank_id = ? AND pool_id = ? AND question_type = 'subjective' ORDER BY times_used ASC",
            (bank_id, pool_id)
        ).fetchall()
        if rows:
            conn.close()
            return [dict(r) for r in rows]

    rows = conn.execute(
        "SELECT * FROM questions WHERE bank_id = ? AND pool_id = ? ORDER BY times_used ASC",
        (bank_id, pool_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _save_paper(
    uid: str,
    paper_questions: list,
    answer_key: dict,
    paper_no: int,
    subject_name: str = DEFAULT_SUBJECT_NAME,
    course_code: str = DEFAULT_COURSE_CODE,
    duration: str = DEFAULT_QUIZ_DURATION,
    instructions: str = DEFAULT_QUIZ_INSTRUCTIONS,
    paper_type: str = "objective",
    exam_title: str = DEFAULT_QUIZ_TITLE,
    max_marks: str = DEFAULT_QUIZ_MARKS,
    is_randomized: bool = True,
    exam_date: str = None,
    marks_per_question: str = "",
    bank_id: int = 1,
):
    """Persist a paper to the database."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO papers
           (uid, questions, answer_key, paper_no, subject_name, course_code, duration, instructions,
            paper_type, exam_title, max_marks, is_randomized, exam_date, marks_per_question, bank_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            uid,
            json.dumps(paper_questions),
            json.dumps(answer_key),
            paper_no,
            subject_name,
            course_code,
            duration,
            instructions,
            paper_type,
            exam_title,
            max_marks,
            1 if is_randomized else 0,
            exam_date or datetime.now().strftime("%d-%b-%Y"),
            marks_per_question or "",
            bank_id,
        ),
    )
    conn.commit()
    conn.close()


def generate_papers(
    count: int,
    questions_per_paper: int = 5,
    paper_type: str = "objective",
    subject_name: str = DEFAULT_SUBJECT_NAME,
    course_code: str = DEFAULT_COURSE_CODE,
    duration: str = None,
    instructions: str = None,
    exam_title: str = None,
    max_marks: str = None,
    exam_date: str = None,
    marks_per_question: str = None,
    randomize: bool = True,
    debug_mode: bool = False,
    bank_id: int = 1,
    pool_ids: List[int] = None,
    per_pool: dict = None,
) -> List[dict]:
    """
    Generate `count` question papers (Objective MCQ or Subjective Semester Paper)
    with `questions_per_paper` questions drawn from the selected pools of a bank.
    Questions are spread evenly across the selected pools unless `per_pool`
    ({pool_no: n}) is given. Can be randomized across pools and options, or
    deterministic for standardized master papers.
    """
    bank = get_bank(bank_id)
    if not bank:
        raise ValueError(f"Question bank {bank_id} not found.")

    # Resolve pool selection
    conn = get_connection()
    bank_pools = [r[0] for r in conn.execute(
        "SELECT pool_no FROM pools WHERE bank_id=? ORDER BY pool_no", (bank_id,)).fetchall()]
    non_empty = {r[0] for r in conn.execute(
        "SELECT DISTINCT pool_id FROM questions WHERE bank_id=?", (bank_id,)).fetchall()}
    conn.close()
    # No explicit selection -> use every pool that actually has questions
    selected_pools = sorted(set(pool_ids)) if pool_ids else [p for p in bank_pools if p in non_empty]
    unknown = [p for p in selected_pools if p not in bank_pools]
    if unknown:
        raise ValueError(f"Pool(s) {unknown} do not exist in bank '{bank['name']}'.")
    if not selected_pools:
        raise ValueError("No pools selected.")

    if per_pool:
        per_pool = {int(k): int(v) for k, v in per_pool.items() if int(v) > 0 and int(k) in selected_pools}
        if not per_pool:
            raise ValueError("Per-pool counts must be greater than 0 for at least one selected pool.")
        questions_per_paper = sum(per_pool.values())

    questions_per_paper = max(1, int(questions_per_paper or 5))

    if paper_type == "subjective":
        duration = duration or DEFAULT_SEMESTER_DURATION
        instructions = instructions or DEFAULT_SEMESTER_INSTRUCTIONS
        exam_title = exam_title or DEFAULT_SEMESTER_TITLE
        max_marks = max_marks or f"{questions_per_paper * 10} (10 marks per question)"
    else:
        duration = duration or DEFAULT_QUIZ_DURATION
        instructions = instructions or DEFAULT_QUIZ_INSTRUCTIONS
        exam_title = exam_title or DEFAULT_QUIZ_TITLE
        max_marks = max_marks or f"{questions_per_paper * 2} (2 marks per question)"

    exam_date = (exam_date or "").strip() or datetime.now().strftime("%d-%b-%Y")
    marks_per_question = (marks_per_question or "").strip()

    existing_fingerprints: Set[frozenset] = set()

    # Load existing papers' fingerprints to avoid collision with past exams (if randomized)
    conn = get_connection()
    existing = conn.execute("SELECT questions FROM papers WHERE bank_id = ?", (bank_id,)).fetchall()
    conn.close()
    for row in existing:
        qs = json.loads(row["questions"])
        fp = frozenset(q["question_id"] for q in qs)
        existing_fingerprints.add(fp)

    generated = []

    for _ in range(count):
        retries = 0
        while True:
            retries += 1
            if retries > 100:
                raise RuntimeError(
                    "Cannot generate unique papers — question bank too small. "
                    "Please add more questions to the selected pools."
                )

            pools_map = {}
            for pool_id in selected_pools:
                pool_qs = _get_pool_questions(bank_id, pool_id, question_type=paper_type)
                if not pool_qs:
                    if debug_mode:
                        continue   # skip empty pool silently
                    raise ValueError(
                        f"Pool {pool_id} is empty — add questions or deselect it before generating papers."
                    )
                pools_map[pool_id] = pool_qs

            active_pools = list(pools_map.keys())
            if not active_pools:
                raise ValueError("All selected pools are empty — add questions before generating papers.")

            quota = {p: 0 for p in active_pools}
            if per_pool:
                for p, n in per_pool.items():
                    if p in quota:
                        if n > len(pools_map[p]) and not debug_mode:
                            raise ValueError(
                                f"Pool {p} has only {len(pools_map[p])} question(s) but {n} requested."
                            )
                        quota[p] = min(n, len(pools_map[p]))
            else:
                total_avail = sum(len(pools_map[p]) for p in active_pools)
                if total_avail < questions_per_paper and not debug_mode:
                    raise ValueError(
                        f"Not enough questions in the selected pools: {total_avail} available, "
                        f"but {questions_per_paper} questions per paper requested."
                    )

                target_total = min(questions_per_paper, total_avail)

                while sum(quota.values()) < target_total:
                    eligible = [p for p in active_pools if quota[p] < len(pools_map[p])]
                    if not eligible:
                        break
                    needed = target_total - sum(quota.values())
                    if needed >= len(eligible):
                        for p in eligible:
                            quota[p] += 1
                    else:
                        chosen_pools = random.sample(eligible, needed) if randomize else eligible[:needed]
                        for p in chosen_pools:
                            quota[p] += 1

            selected_raw = []
            for pool_id in active_pools:
                k = quota[pool_id]
                if k > 0:
                    picked = _weighted_sample(pools_map[pool_id], k, randomize=randomize)
                    selected_raw.extend(picked)

            if randomize:
                random.shuffle(selected_raw)

            fingerprint = frozenset(q["id"] for q in selected_raw)
            if randomize and fingerprint in existing_fingerprints and count > 1:
                continue

            existing_fingerprints.add(fingerprint)
            break

        # Assign paper_no first, then build the deterministic UID from it
        paper_no = _next_paper_no(bank_id)
        uid = _make_uid(paper_no, bank["code"])
        while _uid_exists(uid):
            paper_no += 1
            uid = _make_uid(paper_no, bank["code"])

        paper_questions = []
        answer_key = {}

        for idx, q in enumerate(selected_raw):
            if paper_type == "subjective":
                shuffled = {}
                correct = ""
            else:
                if randomize:
                    shuffled = _shuffle_options(q)
                else:
                    shuffled = {
                        "a": q.get("option_a", ""),
                        "b": q.get("option_b", ""),
                        "c": q.get("option_c", ""),
                        "d": q.get("option_d", ""),
                    }
                correct = q.get("correct_opt", "")

            q_marks = q.get("marks")
            if q_marks is None:
                q_marks = 10 if paper_type == "subjective" else 2

            pq = {
                "q_index": idx,
                "question_id": q["id"],
                "text": q["text"],
                "shuffled_options": shuffled,
                "correct_opt": correct,
                "marks": q_marks,
            }
            paper_questions.append(pq)
            answer_key[str(idx)] = correct

        _save_paper(
            uid,
            paper_questions,
            answer_key,
            paper_no,
            subject_name=subject_name,
            course_code=course_code,
            duration=duration,
            instructions=instructions,
            paper_type=paper_type,
            exam_title=exam_title,
            max_marks=max_marks,
            is_randomized=randomize,
            exam_date=exam_date,
            marks_per_question=marks_per_question,
            bank_id=bank_id,
        )
        _increment_times_used([q["id"] for q in selected_raw])

        # Eagerly compile PDF so it lands in generated_papers/ immediately
        try:
            from app.services.latex_gen import get_or_compile_pdf
            get_or_compile_pdf(uid)
        except Exception:
            pass  # PDF compilation is best-effort; paper is still saved in DB

        generated.append({
            "uid": uid,
            "paper_no": paper_no,
            "subject_name": subject_name,
            "course_code": course_code,
            "duration": duration,
            "instructions": instructions,
            "paper_type": paper_type,
            "exam_title": exam_title,
            "max_marks": max_marks,
            "exam_date": exam_date,
            "marks_per_question": marks_per_question,
            "is_randomized": randomize,
            "bank_id": bank_id,
            "questions": paper_questions,
        })


    return generated


def get_paper(uid: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM papers WHERE uid=?", (uid,)).fetchone()
    conn.close()
    if not row:
        return None
    pt = row["paper_type"] or "objective"
    return {
        "uid":                row["uid"],
        "paper_no":           row["paper_no"],
        "created_at":         row["created_at"],
        "subject_name":       row["subject_name"] or DEFAULT_SUBJECT_NAME,
        "course_code":        row["course_code"] or DEFAULT_COURSE_CODE,
        "duration":           row["duration"] or (DEFAULT_SEMESTER_DURATION if pt == "subjective" else DEFAULT_QUIZ_DURATION),
        "instructions":       row["instructions"] or (DEFAULT_SEMESTER_INSTRUCTIONS if pt == "subjective" else DEFAULT_QUIZ_INSTRUCTIONS),
        "paper_type":         pt,
        "exam_title":         row["exam_title"] or (DEFAULT_SEMESTER_TITLE if pt == "subjective" else DEFAULT_QUIZ_TITLE),
        "max_marks":          row["max_marks"] or (DEFAULT_SEMESTER_MARKS if pt == "subjective" else DEFAULT_QUIZ_MARKS),
        "exam_date":          row["exam_date"] or datetime.now().strftime("%d-%b-%Y"),
        "marks_per_question": row["marks_per_question"] or "",
        "is_randomized":      bool(row["is_randomized"]) if row["is_randomized"] is not None else True,
        "bank_id":            row["bank_id"] if row["bank_id"] is not None else 1,
        "questions":          json.loads(row["questions"]),
        "answer_key":         json.loads(row["answer_key"]),
    }


def list_papers(bank_id: int = None) -> List[dict]:
    conn = get_connection()
    where = "WHERE bank_id = ?" if bank_id is not None else ""
    params = (bank_id,) if bank_id is not None else ()
    rows = conn.execute(
        f"""SELECT uid, paper_no, created_at, subject_name, course_code, duration, instructions,
                  paper_type, exam_title, max_marks, is_randomized, exam_date, marks_per_question, bank_id
           FROM papers {where} ORDER BY created_at DESC, paper_no DESC""",
        params,
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        pt = r["paper_type"] or "objective"
        result.append({
            "uid":                r["uid"],
            "paper_no":           r["paper_no"],
            "created_at":         r["created_at"],
            "subject_name":       r["subject_name"] or DEFAULT_SUBJECT_NAME,
            "course_code":        r["course_code"] or DEFAULT_COURSE_CODE,
            "duration":           r["duration"] or (DEFAULT_SEMESTER_DURATION if pt == "subjective" else DEFAULT_QUIZ_DURATION),
            "instructions":       r["instructions"] or (DEFAULT_SEMESTER_INSTRUCTIONS if pt == "subjective" else DEFAULT_QUIZ_INSTRUCTIONS),
            "paper_type":         pt,
            "exam_title":         r["exam_title"] or (DEFAULT_SEMESTER_TITLE if pt == "subjective" else DEFAULT_QUIZ_TITLE),
            "max_marks":          r["max_marks"] or (DEFAULT_SEMESTER_MARKS if pt == "subjective" else DEFAULT_QUIZ_MARKS),
            "exam_date":          r["exam_date"] or datetime.now().strftime("%d-%b-%Y"),
            "marks_per_question": r["marks_per_question"] or "",
            "is_randomized":      bool(r["is_randomized"]) if r["is_randomized"] is not None else True,
            "bank_id":            r["bank_id"],
        })
    return result


def get_all_papers_detailed(bank_id: int = None) -> List[dict]:
    conn = get_connection()
    if bank_id is not None:
        rows = conn.execute(
            "SELECT * FROM papers WHERE bank_id = ? ORDER BY paper_no ASC", (bank_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM papers ORDER BY bank_id ASC, paper_no ASC").fetchall()
    conn.close()
    result = []
    for r in rows:
        pt = r["paper_type"] or "objective"
        result.append({
            "uid":                r["uid"],
            "paper_no":           r["paper_no"],
            "created_at":         r["created_at"],
            "subject_name":       r["subject_name"] or DEFAULT_SUBJECT_NAME,
            "course_code":        r["course_code"] or DEFAULT_COURSE_CODE,
            "duration":           r["duration"] or (DEFAULT_SEMESTER_DURATION if pt == "subjective" else DEFAULT_QUIZ_DURATION),
            "instructions":       r["instructions"] or (DEFAULT_SEMESTER_INSTRUCTIONS if pt == "subjective" else DEFAULT_QUIZ_INSTRUCTIONS),
            "paper_type":         pt,
            "exam_title":         r["exam_title"] or (DEFAULT_SEMESTER_TITLE if pt == "subjective" else DEFAULT_QUIZ_TITLE),
            "max_marks":          r["max_marks"] or (DEFAULT_SEMESTER_MARKS if pt == "subjective" else DEFAULT_QUIZ_MARKS),
            "exam_date":          r["exam_date"] or datetime.now().strftime("%d-%b-%Y"),
            "marks_per_question": r["marks_per_question"] or "",
            "is_randomized":      bool(r["is_randomized"]) if r["is_randomized"] is not None else True,
            "bank_id":            r["bank_id"],
            "questions":          json.loads(r["questions"]),
            "answer_key":         json.loads(r["answer_key"]),
        })
    return result
