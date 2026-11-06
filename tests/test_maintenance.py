import unittest
import tempfile
import sqlite3
from pathlib import Path
from app.database import create_database_backup, BACKUPS_DIR, get_connection
from app.services.maintenance import purge_stale_build_artifacts

class TestMaintenanceAndBackups(unittest.TestCase):

    def test_database_backup_creation(self):
        backup_file = create_database_backup("test_suite")
        self.assertIsNotNone(backup_file)
        self.assertTrue(backup_file.exists())
        self.assertTrue(backup_file.stat().st_size > 0)

        # Verify the backup can be read as a valid SQLite DB
        conn = sqlite3.connect(str(backup_file))
        res = conn.execute("SELECT COUNT(*) FROM banks").fetchone()[0]
        self.assertGreaterEqual(res, 1)
        conn.close()

    def test_purge_stale_build_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create sample files
            pdf_file = tmppath / "paper.pdf"
            tex_file = tmppath / "paper.tex"
            aux_file = tmppath / "paper.aux"
            log_file = tmppath / "paper.log"

            pdf_file.write_text("dummy pdf")
            tex_file.write_text("dummy tex")
            aux_file.write_text("dummy aux")
            log_file.write_text("dummy log")

            result = purge_stale_build_artifacts(tmppath)
            self.assertEqual(result["purged_files"], 2)
            self.assertTrue(pdf_file.exists())
            self.assertTrue(tex_file.exists())
            self.assertFalse(aux_file.exists())
            self.assertFalse(log_file.exists())

if __name__ == "__main__":
    unittest.main()
