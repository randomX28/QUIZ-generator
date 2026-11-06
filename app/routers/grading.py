import io
import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from app.models import GradeRequest, GradeResponse, ROLL_NO_REGEX
from app.services.grader import grade_student
from app.services.generator import get_paper

router = APIRouter(prefix="/api/grade", tags=["Grading"])


@router.get("/template")
def download_grading_template():
    """Generate and return a formatted Excel template for TA bulk grading."""
    from openpyxl.utils import get_column_letter
    from app.services.generator import get_all_papers_detailed

    papers = get_all_papers_detailed()
    max_q = max((len(p.get("questions", [])) for p in papers), default=5)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TA_Grading"

    # Styling definitions
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=11)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    headers = ["Admission_No", "Paper_Code"] + [f"Q{i}" for i in range(1, max_q + 1)] + ["TA_Name"]
    ws.append(headers)

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    # Sample rows
    cycle_opts = ["a", "b", "c", "d"]
    sample_rows = [
        ["21CS0001", "CD-2026-1"] + [cycle_opts[i % 4] for i in range(max_q)] + ["TA_John"],
        ["21CS0002", "CD-2026-2"] + [cycle_opts[(i + 1) % 4] for i in range(max_q)] + ["TA_John"],
    ]

    for row_data in sample_rows:
        ws.append(row_data)
        current_row = ws.max_row
        for col_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = data_font
            cell.alignment = center_align if (2 < col_idx < len(row_data)) else left_align
            cell.border = thin_border

    # Set column widths
    ws.column_dimensions["A"].width = 18  # Admission_No
    ws.column_dimensions["B"].width = 16  # Paper_Code
    for c_idx in range(3, 3 + max_q):
        ws.column_dimensions[get_column_letter(c_idx)].width = 8
    ws.column_dimensions[get_column_letter(3 + max_q)].width = 15  # TA_Name

    ws.row_dimensions[1].height = 26

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ta_grading_template.xlsx"}
    )


@router.post("/upload-excel")
async def bulk_grade_excel(file: UploadFile = File(...)):
    """Upload an Excel file containing multiple students' responses to grade in bulk."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .xlsx or .xls file.")

    contents = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")

    rows = list(ws.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        raise HTTPException(status_code=400, detail="Excel sheet is empty or has no data rows.")

    # Parse headers
    header_row = [str(cell).strip().lower() if cell is not None else "" for cell in rows[0]]
    
    col_map = {}
    q_col_map = {}  # {0: col_idx_for_q1, 1: col_idx_for_q2, ...}
    for idx, h in enumerate(header_row):
        h_clean = h.replace(" ", "_").replace(".", "").replace("-", "_")
        if h_clean in ("admission_no", "admission_number", "roll_no", "roll_number", "student_id", "rollno", "admissionno"):
            col_map["roll_no"] = idx
        elif h_clean in ("paper_code", "paper_uid", "paper_no", "papercode", "paper"):
            col_map["paper_code"] = idx
        elif h_clean in ("ta_name", "ta", "entered_by", "evaluator"):
            col_map["ta_name"] = idx
        else:
            q_match = re.match(r"^q(?:uestion)?_?(\d+)$", h_clean)
            if q_match:
                q_num = int(q_match.group(1))
                if q_num >= 1:
                    q_col_map[q_num - 1] = idx

    missing_fields = [rf for rf in ["roll_no", "paper_code"] if rf not in col_map]
    if not q_col_map:
        missing_fields.append("Q1..QN")
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns in Excel: {', '.join(missing_fields)}. Expected: Admission_No, Paper_Code, Q1, Q2, ..."
        )

    results = []
    errors = []

    for row_idx, row_values in enumerate(rows[1:], start=2):
        if not any(row_values):
            continue  # Skip completely empty rows

        def get_val(key):
            idx = col_map.get(key)
            if idx is not None and idx < len(row_values):
                val = row_values[idx]
                return str(val).strip() if val is not None else ""
            return ""

        roll_no = get_val("roll_no").upper()
        paper_code = get_val("paper_code").upper()
        ta_name = get_val("ta_name") or "TA"

        if not roll_no:
            errors.append({"row": row_idx, "roll_no": "—", "error": "Missing Admission/Roll Number."})
            continue

        if not re.match(ROLL_NO_REGEX, roll_no):
            errors.append({
                "row": row_idx,
                "roll_no": roll_no,
                "error": f"Invalid Roll Number format '{roll_no}'. Must be 2 digits, 2 uppercase letters, 4 digits (e.g. 21CS0001)."
            })
            continue

        if not paper_code:
            errors.append({"row": row_idx, "roll_no": roll_no, "error": "Missing Paper Code."})
            continue

        # If user passed just a number like "1", format to "CD-YYYY-1"
        if paper_code.isdigit():
            from datetime import datetime
            paper_code = f"CD-{datetime.now().year}-{paper_code}"

        # Collect Q1..QN responses
        responses = {}
        for q_idx, c_idx in q_col_map.items():
            if c_idx < len(row_values) and row_values[c_idx] is not None:
                ans = str(row_values[c_idx]).strip().lower()
                if ans:
                    responses[q_idx] = ans

        try:
            graded = grade_student(
                roll_no=roll_no,
                paper_uid=paper_code,
                responses=responses,
                entered_by=ta_name
            )
            results.append({
                "row": row_idx,
                "roll_no": roll_no,
                "paper_uid": paper_code,
                "score": graded["score"],
                "total": graded["total"],
                "ta_name": ta_name,
            })
        except ValueError as e:
            errors.append({
                "row": row_idx,
                "roll_no": roll_no,
                "paper_code": paper_code,
                "error": str(e)
            })
        except Exception as e:
            errors.append({
                "row": row_idx,
                "roll_no": roll_no,
                "paper_code": paper_code,
                "error": f"Evaluation error: {str(e)}"
            })

    return {
        "total_processed": len(results) + len(errors),
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    }


@router.get("/paper/{uid}")
def load_paper_for_ta(uid: str):
    """Load a paper's questions for display in the TA entry form."""
    paper = get_paper(uid)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper code '{uid}' not found.")
    # Return questions with their shuffled options (no correct answer exposed)
    questions = []
    for q in paper["questions"]:
        questions.append({
            "q_index": q["q_index"],
            "text": q["text"],
            "options": q["shuffled_options"],  # {'a': text, 'b': text, ...}
        })
    return {"uid": uid, "created_at": paper["created_at"], "questions": questions}


@router.post("", response_model=GradeResponse)
def submit_grades(req: GradeRequest):
    """TA submits a student's answers — returns instant graded result."""
    # Validate responses
    if len(req.responses) == 0:
        raise HTTPException(status_code=400, detail="No responses provided.")
    for label in req.responses.values():
        if label not in ("a", "b", "c", "d"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid option '{label}'. Must be a, b, c, or d."
            )
    try:
        result = grade_student(
            roll_no=req.roll_no,
            paper_uid=req.paper_uid,
            responses={int(k): v for k, v in req.responses.items()},
            entered_by=req.entered_by or "TA",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result

