import unittest
import sqlite3
from unittest.mock import patch
from app.database import get_db

class TestDatabaseContext(unittest.TestCase):

    def test_get_db_commits_on_success(self):
        with patch("app.database.get_connection") as mock_conn_fn:
            mock_conn = mock_conn_fn.return_value
            with get_db() as conn:
                self.assertEqual(conn, mock_conn)
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()
            mock_conn.rollback.assert_not_called()

    def test_get_db_rolls_back_on_error(self):
        with patch("app.database.get_connection") as mock_conn_fn:
            mock_conn = mock_conn_fn.return_value
            with self.assertRaises(ValueError):
                with get_db() as conn:
                    raise ValueError("Simulated DB error")
            mock_conn.commit.assert_not_called()
            mock_conn.rollback.assert_called_once()
            mock_conn.close.assert_called_once()

if __name__ == "__main__":
    unittest.main()

