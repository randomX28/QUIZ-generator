import csv
import io
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services.grader import get_all_results, get_result_by_roll

router = APIRouter(prefix="/api/results", tags=["Results"])


@router.get("")
def all_results(bank_id: int = None):
    return get_all_results(bank_id)


@router.get("/roll/{roll_no}")
def results_by_roll(roll_no: str, bank_id: int = None):
    results = get_result_by_roll(roll_no, bank_id)
    if not results:
        raise HTTPException(status_code=404, detail=f"No results found for roll number '{roll_no}'.")
    return results


@router.get("/export/csv")
def export_csv(bank_id: int = None):
    """Export all results as CSV — one row per student."""
    results = get_all_results(bank_id)
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Roll No", "Paper Code", "Score", "Total", "Entered By", "Entered At"])
    for r in results:
        writer.writerow([
            r["roll_no"], r["paper_uid"], r["score"], r["total"],
            r["entered_by"], r["entered_at"]
        ])

    output.seek(0)
    buf = io.BytesIO(output.getvalue().encode("utf-8"))
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=results.csv"}
    )


@router.delete("", status_code=200)
def delete_all_results(bank_id: int = None):
    """Clear and nullify graded student results (of one bank, or all if bank_id is omitted)."""
    from app.services.grader import clear_all_results
    clear_all_results(bank_id)
    return {"message": "All student results have been successfully nullified.", "deleted": "all"}


@router.delete("/{result_id}", status_code=200)
def delete_single_result(result_id: int):
    """Delete a single student result by ID."""
    from app.services.grader import delete_result_by_id
    success = delete_result_by_id(result_id)
    if not success:
        raise HTTPException(status_code=404, detail="Result not found.")
    return {"message": f"Result {result_id} deleted successfully.", "deleted": result_id}


@router.get("/stats")
def class_stats(bank_id: int = None):
    """Return aggregate statistics across all students."""
    results = get_all_results(bank_id)
    if not results:
        return {
            "count": 0,
            "average": 0,
            "max": 0,
            "min": 0,
            "total_marks": 10,
            "distribution": {str(i): 0 for i in range(11)},
            "pass_rate": 0,
        }

    scores = [r["score"] for r in results]
    total_marks = max((r.get("total", 10) for r in results), default=10)
    total = len(scores)
    avg = sum(scores) / total
    max_bucket = max(total_marks, max(scores, default=10))
    distribution = {str(i): scores.count(i) for i in range(max_bucket + 1)}

    return {
        "count": total,
        "average": round(avg, 2),
        "max": max(scores),
        "min": min(scores),
        "total_marks": total_marks,
        "distribution": distribution,
        "pass_rate": round(sum(1 for r in results if r["score"] >= (r.get("total", 10) * 0.5)) / total * 100, 1),
    }
