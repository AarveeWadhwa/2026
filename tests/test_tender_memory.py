import tempfile
import unittest
from pathlib import Path
from backend.services.tender_memory import TenderMemoryStore

class TenderMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = TenderMemoryStore(Path(self.tmp.name) / "memory.sqlite3")
        self.company = {"company_name": "Example Ltd", "industry": "IT", "location": "Pune"}
    def tearDown(self): self.tmp.cleanup()
    def test_persists_snapshot_and_increments_cycle(self):
        first = self.store.record_cycle(self.company, "T-1", {"deadline": "2026-11-05"}, {"status": "review"})
        second = self.store.record_cycle(self.company, "T-1", {"deadline": "2026-11-10"}, {"status": "review"})
        self.assertEqual(first["cycle_count"], 1)
        self.assertEqual(second["cycle_count"], 2)
        history = self.store.get_company_history(self.company)
        self.assertEqual(history["T-1"]["snapshot"]["deadline"], "2026-11-10")
    def test_company_histories_are_scoped(self):
        self.store.record_cycle(self.company, "T-1", {}, {})
        other = {"company_name": "Other Ltd", "industry": "IT", "location": "Pune"}
        self.assertEqual(self.store.get_company_history(other), {})
    def test_clear_company_history(self):
        self.store.record_cycle(self.company, "T-1", {}, {})
        self.assertEqual(self.store.clear_company(self.company), 1)
        self.assertEqual(self.store.get_company_history(self.company), {})
