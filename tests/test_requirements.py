
import unittest
from pathlib import Path
from backend.agents.requirement_agent import TenderRequirementAgent
from backend.services.document_parser import extract_text


ROOT = Path(__file__).resolve().parents[1]


class RequirementTests(unittest.TestCase):
    def test_extracts_common_fields(self):
        path = ROOT / "data" / "sample_tenders" / "tender_001.txt"
        text = extract_text(path)
        result = TenderRequirementAgent().extract(text, "BP-2026-001")
        self.assertEqual(result["tender_id"], "BP-2026-001")
        self.assertIsNotNone(result["eligibility"]["minimum_turnover"])
        self.assertIsNotNone(result["eligibility"]["minimum_experience"])
        self.assertIsNotNone(result["deadlines"]["bid_submission_deadline"])
        self.assertTrue(result["documents_required"])
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
