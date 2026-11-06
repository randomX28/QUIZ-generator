"""Maintenance utilities: Cache cleanup, disk garbage collection, and database backups."""
import os
import glob
from pathlib import Path
from app.config import settings

STALE_EXTENSIONS = {".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk", ".synctex.gz"}


def purge_stale_build_artifacts(target_dir: Path | str | None = None) -> dict:
    """Scan output directory and remove LaTeX auxiliary files, keeping PDFs and TEX files.
    
    Returns: {"purged_files": int, "freed_bytes": int}
    """
    base_dir = Path(target_dir) if target_dir else settings.OUTPUT_DIR
    if not base_dir.exists():
        return {"purged_files": 0, "freed_bytes": 0}

    purged_count = 0
    freed_bytes = 0

    for root, _, files in os.walk(base_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in STALE_EXTENSIONS:
                fp = Path(root) / f
                try:
                    freed_bytes += fp.stat().st_size
                    fp.unlink()
                    purged_count += 1
                except OSError:
                    pass

    return {"purged_files": purged_count, "freed_bytes": freed_bytes}
