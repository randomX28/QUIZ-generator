import os
import re
import glob
from fastapi import APIRouter, HTTPException
from app.models import BankCreate, PoolCreate
from app.database import get_connection

router = APIRouter(prefix="/api/banks", tags=["Banks"])


def _bank_or_404(conn, bank_id: int):
    row = conn.execute("SELECT * FROM banks WHERE id=?", (bank_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Bank not found.")
    return row


def _make_code(name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name)
    if not words:
        return "QB"
    if len(words) == 1:
        return words[0][:4].upper()
    return "".join(w[0] for w in words)[:5].upper()


def _bank_summary(conn, row) -> dict:
    d = dict(row)
    d["pool_count"] = conn.execute("SELECT COUNT(*) FROM pools WHERE bank_id=?", (row["id"],)).fetchone()[0]
    d["question_count"] = conn.execute("SELECT COUNT(*) FROM questions WHERE bank_id=?", (row["id"],)).fetchone()[0]
    d["paper_count"] = conn.execute("SELECT COUNT(*) FROM papers WHERE bank_id=?", (row["id"],)).fetchone()[0]
    return d


# ── Banks ──────────────────────────────────────────────────────────────────

@router.get("")
def list_banks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM banks ORDER BY id").fetchall()
    out = [_bank_summary(conn, r) for r in rows]
    conn.close()
    return out


@router.post("", status_code=201)
def create_bank(b: BankCreate):
    name = b.name.strip()
    code = re.sub(r"[^A-Za-z0-9]", "", (b.code or "")).upper() or _make_code(name)
    conn = get_connection()
    if conn.execute("SELECT 1 FROM banks WHERE lower(name)=lower(?)", (name,)).fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"A bank named '{name}' already exists.")
    if conn.execute("SELECT 1 FROM banks WHERE code=?", (code,)).fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"Paper code prefix '{code}' is already used by another bank.")
    cur = conn.execute(
        "INSERT INTO banks (name, code, subject_name, course_code) VALUES (?, ?, ?, ?)",
        (name, code, (b.subject_name or name).strip(), (b.course_code or "").strip()),
    )
    bank_id = cur.lastrowid
    for n in range(1, (b.num_pools or 5) + 1):
        conn.execute("INSERT INTO pools (bank_id, pool_no, name) VALUES (?, ?, ?)", (bank_id, n, f"Pool {n}"))
    conn.commit()
    row = conn.execute("SELECT * FROM banks WHERE id=?", (bank_id,)).fetchone()
    out = _bank_summary(conn, row)
    conn.close()
    return out


@router.put("/{bank_id}")
def update_bank(bank_id: int, b: BankCreate):
    conn = get_connection()
    _bank_or_404(conn, bank_id)
    name = b.name.strip()
    dup = conn.execute("SELECT 1 FROM banks WHERE lower(name)=lower(?) AND id<>?", (name, bank_id)).fetchone()
    if dup:
        conn.close()
        raise HTTPException(status_code=400, detail=f"A bank named '{name}' already exists.")
    # The code prefix is intentionally NOT changed: it is baked into issued paper codes.
    conn.execute(
        "UPDATE banks SET name=?, subject_name=?, course_code=? WHERE id=?",
        (name, (b.subject_name or name).strip(), (b.course_code or "").strip(), bank_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM banks WHERE id=?", (bank_id,)).fetchone()
    out = _bank_summary(conn, row)
    conn.close()
    return out


@router.delete("/{bank_id}")
def delete_bank(bank_id: int):
    from app.services.latex_gen import PDF_CACHE_DIR
    conn = get_connection()
    _bank_or_404(conn, bank_id)
    if conn.execute("SELECT COUNT(*) FROM banks").fetchone()[0] <= 1:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot delete the only remaining bank.")

    uids = [r[0] for r in conn.execute("SELECT uid FROM papers WHERE bank_id=?", (bank_id,)).fetchall()]
    for uid in uids:
        conn.execute("DELETE FROM student_results WHERE paper_uid=?", (uid,))
    conn.execute("DELETE FROM papers WHERE bank_id=?", (bank_id,))
    conn.execute("DELETE FROM questions WHERE bank_id=?", (bank_id,))
    conn.execute("DELETE FROM pools WHERE bank_id=?", (bank_id,))
    conn.execute("DELETE FROM banks WHERE id=?", (bank_id,))
    conn.commit()
    conn.close()

    for uid in uids:
        p = os.path.join(PDF_CACHE_DIR, f"{uid}.pdf")
        if os.path.exists(p):
            os.remove(p)
    for p in glob.glob(os.path.join(PDF_CACHE_DIR, f"*_bank{bank_id}.pdf")):
        os.remove(p)

    # Clean up partitioned directory for this bank
    import shutil
    from app.config import settings
    bank_dir = str(settings.get_bank_output_dir(bank_id))
    if os.path.exists(bank_dir):
        shutil.rmtree(bank_dir, ignore_errors=True)

    return {"deleted": bank_id, "papers_removed": len(uids)}


# ── Pools ──────────────────────────────────────────────────────────────────

@router.get("/{bank_id}/pools")
def list_pools(bank_id: int):
    conn = get_connection()
    _bank_or_404(conn, bank_id)
    rows = conn.execute(
        """SELECT p.pool_no, p.name,
                  (SELECT COUNT(*) FROM questions q WHERE q.bank_id=p.bank_id AND q.pool_id=p.pool_no) AS count,
                  (SELECT COALESCE(SUM(times_used),0) FROM questions q WHERE q.bank_id=p.bank_id AND q.pool_id=p.pool_no) AS total_uses
           FROM pools p WHERE p.bank_id=? ORDER BY p.pool_no""",
        (bank_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/{bank_id}/pools", status_code=201)
def add_pool(bank_id: int, p: PoolCreate = PoolCreate()):
    conn = get_connection()
    _bank_or_404(conn, bank_id)
    nxt = conn.execute("SELECT COALESCE(MAX(pool_no),0)+1 FROM pools WHERE bank_id=?", (bank_id,)).fetchone()[0]
    name = (p.name or "").strip() or f"Pool {nxt}"
    conn.execute("INSERT INTO pools (bank_id, pool_no, name) VALUES (?, ?, ?)", (bank_id, nxt, name))
    conn.commit()
    conn.close()
    return {"pool_no": nxt, "name": name, "count": 0, "total_uses": 0}


@router.put("/{bank_id}/pools/{pool_no}")
def rename_pool(bank_id: int, pool_no: int, p: PoolCreate):
    conn = get_connection()
    _bank_or_404(conn, bank_id)
    name = (p.name or "").strip() or f"Pool {pool_no}"
    cur = conn.execute("UPDATE pools SET name=? WHERE bank_id=? AND pool_no=?", (name, bank_id, pool_no))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Pool not found.")
    return {"pool_no": pool_no, "name": name}


@router.delete("/{bank_id}/pools/{pool_no}")
def delete_pool(bank_id: int, pool_no: int, with_questions: bool = False):
    conn = get_connection()
    _bank_or_404(conn, bank_id)
    count = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE bank_id=? AND pool_id=?", (bank_id, pool_no)
    ).fetchone()[0]
    if count and not with_questions:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Pool has {count} question(s). Delete them first or confirm deleting the pool with its questions.",
        )
    if conn.execute("SELECT COUNT(*) FROM pools WHERE bank_id=?", (bank_id,)).fetchone()[0] <= 1:
        conn.close()
        raise HTTPException(status_code=400, detail="A bank needs at least one pool.")
    conn.execute("DELETE FROM questions WHERE bank_id=? AND pool_id=?", (bank_id, pool_no))
    conn.execute("DELETE FROM pools WHERE bank_id=? AND pool_no=?", (bank_id, pool_no))
    conn.commit()
    conn.close()
    return {"deleted": pool_no, "questions_removed": count}

