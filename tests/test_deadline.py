
import unittest
from backend.agents.deadline_agent import DeadlineCorrigendumAgent, normalize_date


class DeadlineTests(unittest.TestCase):
    def test_detects_deadline_extension(self):
        result = DeadlineCorrigendumAgent().compare(
            {"tender_id": "T1", "deadline": "2026-11-05"},
            {"tender_id": "T1", "deadline": "12-Nov-2026"},
        )
        self.assertTrue(result["has_changes"])
        self.assertEqual(result["changes"][0]["field"], "deadline")

    def test_normalizes_supported_date(self):
        self.assertEqual(normalize_date("05-Nov-2026"), "2026-11-05")


if __name__ == "__main__":
    unittest.main()
