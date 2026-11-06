import os
import shutil
import uvicorn
from app.config import settings
from app.database import create_database_backup, get_db


def run_system_sanity_checks():
    print("=" * 70)
    print("🏛️  IIT (ISM) Dhanbad — Exam Paper Generator & Grading System")
    print("=" * 70)

    # 1. Database Check & Automated Snapshot
    print("• Checking local database integrity...")
    try:
        backup = create_database_backup("startup_sanity")
        with get_db() as conn:
            banks = conn.execute("SELECT id, name, code FROM banks").fetchall()
            q_count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
            p_count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        print(f"  ✓ Database verified: {len(banks)} active bank(s), {q_count} questions, {p_count} papers.")
        if backup:
            print(f"  ✓ Pre-launch snapshot saved: {backup.name}")
    except Exception as e:
        print(f"  ⚠ Database check warning: {e}")

    # 2. LaTeX Engine Check
    print("• Checking LaTeX typesetting engine...")
    pdflatex_bin = shutil.which("pdflatex")
    if pdflatex_bin:
        print(f"  ✓ Found pdflatex: {pdflatex_bin}")
    else:
        print("  ⚠ pdflatex was not found on PATH.")
        print("    To install on Ubuntu/Debian: sudo apt update && sudo apt install -y texlive-latex-base texlive-latex-extra")

    # 3. Fast PDF Stitcher Check (Poppler)
    pdfunite_bin = shutil.which("pdfunite")
    if pdfunite_bin:
        print(f"  ✓ Found fast PDF stitcher (pdfunite): {pdfunite_bin}")
    else:
        print("  ℹ pdfunite not found (using standard LaTeX bundle compiler fallback).")

    print(f"• Launching web interface at: http://{settings.HOST}:{settings.PORT}")
    print("=" * 70)


if __name__ == "__main__":
    run_system_sanity_checks()
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
