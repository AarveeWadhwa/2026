import unittest
from backend.services.db import _pg_sql, postgres_enabled

class DatabaseAdapterTests(unittest.TestCase):
    def test_sqlite_autoincrement_schema_converts_for_postgres(self):
        sql = _pg_sql("CREATE TABLE sample (event_id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT NOT NULL)")
        self.assertIn("BIGSERIAL PRIMARY KEY", sql)
        self.assertNotIn("AUTOINCREMENT", sql)

    def test_parameter_placeholders_convert(self):
        self.assertEqual(_pg_sql("SELECT * FROM sample WHERE id=?"), "SELECT * FROM sample WHERE id=%s")

    def test_sqlite_case_literals_convert(self):
        self.assertIn("WHEN 'urgent' THEN 0", _pg_sql('ORDER BY CASE priority WHEN "urgent" THEN 0 END'))

if __name__ == "__main__":
    unittest.main()
