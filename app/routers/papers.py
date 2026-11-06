from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from typing import List
import os
from app.services.generator import generate_papers, list_papers, get_paper
from app.services.latex_gen import get_or_compile_pdf, get_latex_source, PDF_CACHE_DIR

router = APIRouter(prefix="/api/papers", tags=["Papers"])


@router.get("", response_model=List[dict])
def get_all_papers(bank_id: int = None):
    return list_papers(bank_id)


@router.get("/progress/{job_id}")
async def get_generation_progress(job_id: str):
    """Server-Sent Events (SSE) stream reporting real-time batch compilation progress."""
    import json
    import asyncio
    from fastapi.responses import StreamingResponse
    from app.services.job_manager import get_job

    async def event_generator():
        while True:
            job = get_job(job_id)
            if not job:
                yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                break
            yield f"data: {json.dumps(job)}\n\n"
            if job.get("status") in ("completed", "failed"):
                break
            await asyncio.sleep(0.4)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.delete("", status_code=200)
def delete_all_papers(bank_id: int = None):
    from app.database import get_connection
    import glob
    conn = get_connection()
    if bank_id is None:
        conn.execute("DELETE FROM student_results")   # must go first — FK references papers
        conn.execute("DELETE FROM papers")
        conn.execute("UPDATE questions SET times_used = 0")
        conn.commit()
        conn.close()
        for pdf in glob.glob(os.path.join(PDF_CACHE_DIR, "*.pdf")):
            os.remove(pdf)
        return {"deleted": "all"}

    uids = [r[0] for r in conn.execute("SELECT uid FROM papers WHERE bank_id=?", (bank_id,)).fetchall()]
    for uid in uids:
        conn.execute("DELETE FROM student_results WHERE paper_uid=?", (uid,))
    conn.execute("DELETE FROM papers WHERE bank_id=?", (bank_id,))
    conn.execute("UPDATE questions SET times_used = 0 WHERE bank_id=?", (bank_id,))
    conn.commit()
    conn.close()
    # Remove this bank's cached PDFs
    for uid in uids:
        p = os.path.join(PDF_CACHE_DIR, f"{uid}.pdf")
        if os.path.exists(p):
            os.remove(p)
    for p in glob.glob(os.path.join(PDF_CACHE_DIR, f"*_bank{bank_id}.pdf")):
        os.remove(p)
    return {"deleted": "all", "bank_id": bank_id, "papers_removed": len(uids)}


from app.models import (
    GenerateRequest,
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


@router.get("/config/defaults")
def get_paper_defaults():
    """Return default configurations for both objective (quiz) and subjective (semester) generation."""
    from datetime import datetime
    today = datetime.now().strftime("%d-%b-%Y")
    return {
        "subject_name": DEFAULT_SUBJECT_NAME,
        "course_code": DEFAULT_COURSE_CODE,
        "exam_date": today,
        "objective": {
            "paper_type": "objective",
            "subject_name": DEFAULT_SUBJECT_NAME,
            "course_code": DEFAULT_COURSE_CODE,
            "exam_title": DEFAULT_QUIZ_TITLE,
            "max_marks": DEFAULT_QUIZ_MARKS,
            "marks_per_question": "2 Marks",
            "duration": DEFAULT_QUIZ_DURATION,
            "instructions": DEFAULT_QUIZ_INSTRUCTIONS,
            "exam_date": today,
            "count": 30,
            "questions_per_paper": 5,
            "randomize": True,
        },
        "subjective": {
            "paper_type": "subjective",
            "subject_name": DEFAULT_SUBJECT_NAME,
            "course_code": DEFAULT_COURSE_CODE,
            "exam_title": DEFAULT_SEMESTER_TITLE,
            "max_marks": DEFAULT_SEMESTER_MARKS,
            "marks_per_question": "10 Marks",
            "duration": DEFAULT_SEMESTER_DURATION,
            "instructions": DEFAULT_SEMESTER_INSTRUCTIONS,
            "exam_date": today,
            "count": 1,
            "questions_per_paper": 5,
            "randomize": False,
        }
    }


@router.post("/generate", status_code=201)
def generate(
    req: GenerateRequest,
    debug: bool = Query(False, description="Skip empty pools (debug/testing only)")
):
    from datetime import datetime
    pt = "subjective" if req.paper_type == "subjective" else "objective"
    q_per_paper = max(1, req.questions_per_paper or 5)
    subject = (req.subject_name or "").strip() or DEFAULT_SUBJECT_NAME
    course = (req.course_code or "").strip() or DEFAULT_COURSE_CODE
    exam_title = (req.exam_title or "").strip() or (DEFAULT_SEMESTER_TITLE if pt == "subjective" else DEFAULT_QUIZ_TITLE)
    default_mm = f"{q_per_paper * 10} (10 marks per question)" if pt == "subjective" else f"{q_per_paper * 2} (2 marks per question)"
    max_marks = (req.max_marks or "").strip() or default_mm
    duration = (req.duration or "").strip() or (DEFAULT_SEMESTER_DURATION if pt == "subjective" else DEFAULT_QUIZ_DURATION)
    exam_date = (req.exam_date or "").strip() or datetime.now().strftime("%d-%b-%Y")
    marks_per_question = (req.marks_per_question or "").strip()
    randomize = True if req.randomize is None else bool(req.randomize)

    if req.use_default_instructions or not req.instructions or not req.instructions.strip():
        instructions = DEFAULT_SEMESTER_INSTRUCTIONS if pt == "subjective" else DEFAULT_QUIZ_INSTRUCTIONS
    else:
        instructions = req.instructions.strip()

    try:
        papers = generate_papers(
            req.count,
            questions_per_paper=q_per_paper,
            paper_type=pt,
            subject_name=subject,
            course_code=course,
            duration=duration,
            instructions=instructions,
            exam_title=exam_title,
            max_marks=max_marks,
            exam_date=exam_date,
            marks_per_question=marks_per_question,
            randomize=randomize,
            debug_mode=debug,
            bank_id=req.bank_id or 1,
            pool_ids=req.pool_ids,
            per_pool=req.per_pool,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"generated": len(papers), "papers": [p["uid"] for p in papers]}


@router.delete("/{uid}", status_code=200)
def delete_paper(uid: str):
    from app.database import get_connection
    # Check exists
    paper = get_paper(uid)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    # Remove from DB — delete results first to satisfy FK constraint
    conn = get_connection()
    conn.execute("DELETE FROM student_results WHERE paper_uid = ?", (uid,))
    conn.execute("DELETE FROM papers WHERE uid = ?", (uid,))
    conn.commit()
    conn.close()

    # Remove cached PDF if present
    pdf_path = os.path.join(PDF_CACHE_DIR, f"{uid}.pdf")
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    return {"deleted": uid}


@router.get("/bulk/pdf")
def get_bulk_pdf(download: bool = Query(False), bank_id: int = Query(None)):
    from app.services.latex_gen import get_or_compile_bulk_pdf, render_bulk_latex
    try:
        pdf_path = get_or_compile_bulk_pdf(bank_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    disposition = "attachment" if download else "inline"
    if pdf_path:
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            headers={"Content-Disposition": f'{disposition}; filename="all_papers_bundle.pdf"'}
        )
    # Fallback: serve combined LaTeX source
    try:
        latex = render_bulk_latex(bank_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PlainTextResponse(
        content=latex,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'{disposition}; filename="all_papers_bundle.tex"',
            "X-Fallback": "pdflatex-not-available"
        }
    )


@router.get("/bulk/latex", response_class=PlainTextResponse)
def get_bulk_latex(bank_id: int = Query(None)):
    from app.services.latex_gen import render_bulk_latex
    try:
        latex = render_bulk_latex(bank_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PlainTextResponse(
        content=latex,
        headers={"Content-Disposition": 'attachment; filename="all_papers_bundle.tex"'}
    )


# ── Answer Keys & Solution Endpoints for TAs ──────────────────────────────

@router.get("/answer-keys")
def get_all_answer_keys(bank_id: int = None):
    """Return all generated papers with their resolved answer keys and options."""
    from app.services.generator import get_all_papers_detailed
    from app.services.latex_gen import resolve_paper_answer_keys
    papers = get_all_papers_detailed(bank_id)
    return [resolve_paper_answer_keys(p) for p in papers]


@router.get("/answer-keys/export/csv")
def export_answer_keys_csv(bank_id: int = None):
    """Export all paper answer keys as CSV (Paper Code, Paper No, Q1..QN)."""
    from app.services.generator import get_all_papers_detailed
    from app.services.export_service import export_answer_keys_to_csv
    from fastapi.responses import StreamingResponse

    papers = get_all_papers_detailed(bank_id)
    buf = export_answer_keys_to_csv(papers)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="master_answer_keys.csv"'}
    )


@router.get("/answer-keys/export/excel")
def export_answer_keys_excel(bank_id: int = None):
    """Export all paper answer keys as a styled Excel (.xlsx) workbook."""
    from app.services.generator import get_all_papers_detailed
    from app.services.export_service import export_answer_keys_to_excel
    from fastapi.responses import StreamingResponse

    papers = get_all_papers_detailed(bank_id)
    buf = export_answer_keys_to_excel(papers)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="master_answer_keys.xlsx"'}
    )


@router.get("/answer-keys/pdf")
def get_master_answer_keys_pdf(download: bool = Query(False), bank_id: int = Query(None)):
    """Generate and return the Master Answer Key PDF sheet for TAs."""
    from app.services.latex_gen import get_or_compile_answer_keys_pdf, render_answer_keys_latex
    try:
        pdf_path = get_or_compile_answer_keys_pdf(bank_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    disposition = "attachment" if download else "inline"
    if pdf_path:
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            headers={"Content-Disposition": f'{disposition}; filename="master_answer_keys.pdf"'}
        )

    # Fallback to LaTeX source
    try:
        latex = render_answer_keys_latex(bank_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PlainTextResponse(
        content=latex,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'{disposition}; filename="master_answer_keys.tex"',
            "X-Fallback": "pdflatex-not-available"
        }
    )


@router.get("/answer-keys/latex", response_class=PlainTextResponse)
def get_master_answer_keys_latex(bank_id: int = Query(None)):
    """Return LaTeX source code for the Master Answer Key sheet."""
    from app.services.latex_gen import render_answer_keys_latex
    try:
        latex = render_answer_keys_latex(bank_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PlainTextResponse(
        content=latex,
        headers={"Content-Disposition": 'attachment; filename="master_answer_keys.tex"'}
    )


@router.get("/master-paper/pdf")
@router.get("/master/pdf")
def get_master_paper_pdf(bank_id: int = Query(1), download: bool = Query(False)):
    """Generate and return the Master Question Paper PDF containing all bank questions without marked answers."""
    from app.services.latex_gen import get_or_compile_master_paper_pdf, render_master_paper_latex
    try:
        pdf_path = get_or_compile_master_paper_pdf(bank_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    disposition = "attachment" if download else "inline"
    if pdf_path:
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            headers={"Content-Disposition": f'{disposition}; filename="master_question_paper.pdf"'}
        )

    # Fallback to LaTeX source
    try:
        latex = render_master_paper_latex(bank_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return PlainTextResponse(
        content=latex,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'{disposition}; filename="master_question_paper.tex"',
            "X-Fallback": "pdflatex-not-available"
        }
    )


@router.get("/master-paper/latex", response_class=PlainTextResponse)
@router.get("/master/latex", response_class=PlainTextResponse)
def get_master_paper_latex(bank_id: int = Query(1)):
    """Return LaTeX source code for the Master Question Paper containing all bank questions without marked answers."""
    from app.services.latex_gen import render_master_paper_latex
    try:
        latex = render_master_paper_latex(bank_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return PlainTextResponse(
        content=latex,
        headers={"Content-Disposition": 'attachment; filename="master_question_paper.tex"'}
    )


@router.get("/{uid}/answer-key")
def get_single_paper_answer_key(uid: str):
    """Get the resolved answer key and solutions for a specific paper UID."""
    from app.services.latex_gen import resolve_paper_answer_keys
    paper = get_paper(uid)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return resolve_paper_answer_keys(paper)



@router.get("/{uid}")
def get_paper_detail(uid: str):
    paper = get_paper(uid)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    # Strip answer_key from public response
    paper.pop("answer_key", None)
    return paper


@router.get("/{uid}/latex", response_class=PlainTextResponse)
def download_latex(uid: str):
    try:
        latex = get_latex_source(uid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PlainTextResponse(
        content=latex,
        headers={"Content-Disposition": f'attachment; filename="{uid}.tex"'}
    )


@router.get("/{uid}/pdf")
def get_pdf(uid: str, download: bool = Query(False)):
    pdf_path = get_or_compile_pdf(uid)
    disposition = "attachment" if download else "inline"
    if pdf_path:
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            headers={"Content-Disposition": f'{disposition}; filename="{uid}.pdf"'}
        )
    # Fallback: serve LaTeX source
    try:
        latex = get_latex_source(uid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PlainTextResponse(
        content=latex,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'{disposition}; filename="{uid}.tex"',
            "X-Fallback": "pdflatex-not-available"
        }
    )
