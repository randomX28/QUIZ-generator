import json
from typing import Dict, List
from app.services.generator import get_paper
from app.database import get_connection


def grade_student(
    roll_no: str,
    paper_uid: str,
    responses: Dict[int, str],
    entered_by: str = "TA",
) -> dict:
    """
    Grade a student's responses.

    responses: {q_index: chosen_label}  e.g. {0: 'b', 1: 'a', 2: 'd', 3: 'c', 4: 'a'}

    Grading resolves label → option text → compares against correct_opt text.
    This handles per-paper option shuffling transparently.
    """
    paper = get_paper(paper_uid)
    if not paper:
        raise ValueError(f"Paper '{paper_uid}' not found.")

    score = 0
    breakdown = []

    for pq in paper["questions"]:
        idx = pq["q_index"]
        chosen_label = responses.get(idx)
        shuffled = pq["shuffled_options"]

        if chosen_label and chosen_label in shuffled:
            chosen_text = shuffled[chosen_label]
        else:
            chosen_text = "— (no answer)"

        correct_text = pq["correct_opt"]
        is_correct = chosen_text.strip().lower() == correct_text.strip().lower()

        q_marks = pq.get("marks", 2)
        if is_correct:
            score += q_marks

        breakdown.append({
            "q_index": idx,
            "question_text": pq["text"],
            "chosen_text": chosen_text,
            "correct_text": correct_text,
            "is_correct": is_correct,
            "marks": q_marks if is_correct else 0,
            "max_marks": q_marks,
        })

    _save_result(roll_no, paper_uid, score, breakdown, entered_by)

    total_marks = sum(pq.get("marks", 2) for pq in paper["questions"])
    return {
        "roll_no": roll_no,
        "paper_uid": paper_uid,
        "score": score,
        "total": total_marks,
        "breakdown": breakdown,
    }


def _save_result(roll_no, paper_uid, score, breakdown, entered_by):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO student_results (roll_no, paper_uid, score, breakdown, entered_by)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(roll_no, paper_uid) DO UPDATE SET
                 score=excluded.score,
                 breakdown=excluded.breakdown,
                 entered_by=excluded.entered_by,
                 entered_at=CURRENT_TIMESTAMP
            """,
            (roll_no, paper_uid, score, json.dumps(breakdown), entered_by)
        )
        conn.commit()
    finally:
        conn.close()


def _compute_result_total(breakdown: list, paper_uid: str = None) -> int:
    if breakdown:
        return sum(item.get("max_marks", 2) for item in breakdown)
    if paper_uid:
        paper = get_paper(paper_uid)
        if paper and paper.get("questions"):
            return sum(q.get("marks", 2) for q in paper["questions"])
    return 10


def get_all_results(bank_id: int = None) -> List[dict]:
    conn = get_connection()
    if bank_id is None:
        rows = conn.execute(
            "SELECT * FROM student_results ORDER BY entered_at DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT sr.* FROM student_results sr
               JOIN papers p ON p.uid = sr.paper_uid
               WHERE p.bank_id = ? ORDER BY sr.entered_at DESC""",
            (bank_id,),
        ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["breakdown"] = json.loads(d["breakdown"])
        d["total"] = _compute_result_total(d["breakdown"], d.get("paper_uid"))
        results.append(d)
    return results


def get_result_by_roll(roll_no: str, bank_id: int = None) -> List[dict]:
    conn = get_connection()
    if bank_id is None:
        rows = conn.execute(
            "SELECT * FROM student_results WHERE roll_no=? ORDER BY entered_at DESC",
            (roll_no,)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT sr.* FROM student_results sr
               JOIN papers p ON p.uid = sr.paper_uid
               WHERE sr.roll_no=? AND p.bank_id=? ORDER BY sr.entered_at DESC""",
            (roll_no, bank_id),
        ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["breakdown"] = json.loads(d["breakdown"])
        d["total"] = _compute_result_total(d["breakdown"], d.get("paper_uid"))
        results.append(d)
    return results


def clear_all_results(bank_id: int = None):
    """Delete all records from student_results (optionally only those of one bank)."""
    conn = get_connection()
    if bank_id is None:
        conn.execute("DELETE FROM student_results")
    else:
        conn.execute(
            "DELETE FROM student_results WHERE paper_uid IN (SELECT uid FROM papers WHERE bank_id=?)",
            (bank_id,),
        )
    conn.commit()
    conn.close()


def delete_result_by_id(result_id: int) -> bool:
    """Delete a single result by ID."""
    conn = get_connection()
    cur = conn.execute("DELETE FROM student_results WHERE id=?", (result_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


