"""Export service for generated answer keys (CSV and Excel)."""
import csv
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from app.services.latex_gen import resolve_paper_answer_keys


def export_answer_keys_to_csv(papers: list) -> io.BytesIO:
    """Export papers and their answer keys as CSV format in BytesIO."""
    max_q = max((len(p.get("questions", [])) for p in papers), default=5)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Paper No", "Paper Code"] + [f"Q{i}" for i in range(1, max_q + 1)] + ["Created At"])
    for p in papers:
        rp = resolve_paper_answer_keys(p)
        keys = rp["keys"]
        writer.writerow(
            [rp["paper_no"], rp["uid"]]
            + [keys.get(str(i), "") for i in range(max_q)]
            + [rp.get("created_at", "")]
        )

    output.seek(0)
    return io.BytesIO(output.getvalue().encode("utf-8"))


def export_answer_keys_to_excel(papers: list) -> io.BytesIO:
    """Export papers and their answer keys as styled Excel workbook in BytesIO."""
    max_q = max((len(p.get("questions", [])) for p in papers), default=5)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Master_Answer_Keys"

    # Styling
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    headers = ["Paper No", "Paper Code"] + [f"Q{i}" for i in range(1, max_q + 1)] + ["Created At"]
    ws.append(headers)

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    # Color fills for answers A, B, C, D
    opt_fills = {
        "A": PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid"),
        "B": PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid"),
        "C": PatternFill(start_color="FEFCE8", end_color="FEFCE8", fill_type="solid"),
        "D": PatternFill(start_color="FAF5FF", end_color="FAF5FF", fill_type="solid"),
    }

    q_col_indices = set(range(3, 3 + max_q))

    for p in papers:
        rp = resolve_paper_answer_keys(p)
        keys = rp["keys"]
        row_data = (
            [rp["paper_no"], rp["uid"]]
            + [keys.get(str(i), "") for i in range(max_q)]
            + [rp.get("created_at", "")]
        )
        ws.append(row_data)
        curr_row = ws.max_row
        for col_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=curr_row, column=col_idx)
            cell.border = thin_border
            if col_idx == 1 or col_idx in q_col_indices:
                cell.alignment = center_align
            else:
                cell.alignment = left_align

            # Color code answer columns Q1..QN
            if col_idx in q_col_indices:
                val = str(cell.value)
                if val in opt_fills:
                    cell.fill = opt_fills[val]
                    cell.font = Font(bold=True)

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 18
    for c_idx in range(3, 3 + max_q):
        ws.column_dimensions[get_column_letter(c_idx)].width = 8
    ws.column_dimensions[get_column_letter(3 + max_q)].width = 22

    ws.row_dimensions[1].height = 26

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

