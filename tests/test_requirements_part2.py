import unittest
from pathlib import Path

from backend.agents.requirement_agent import TenderRequirementAgent
from backend.services.document_parser import extract_document, extract_text

ROOT = Path(__file__).resolve().parents[1]


class RequirementPartTwoTests(unittest.TestCase):
    def test_normalizes_indian_amounts_and_deadline(self):
        text = (ROOT / "data/sample_tenders/tender_001.txt").read_text(encoding="utf-8")
        result = TenderRequirementAgent().extract(text, "BP-2026-001")
        normalized = result["normalized_requirements"]
        self.assertEqual(normalized["minimum_annual_turnover_inr"], 10_000_000)
        self.assertEqual(normalized["emd_inr"], 50_000)
        self.assertEqual(normalized["tender_fee_inr"], 2_000)
        self.assertEqual(normalized["minimum_experience_months"], 36)
        self.assertEqual(normalized["bid_submission_deadline_iso"], "2026-11-05")

    def test_extracts_evidence_and_review_flag(self):
        text = (ROOT / "data/sample_tenders/tender_004.txt").read_text(encoding="utf-8")
        result = TenderRequirementAgent().extract(text, "BP-2026-004")
        self.assertTrue(result["evidence"]["minimum_turnover"])
        self.assertTrue(result["evidence"]["emd"])
        self.assertTrue(result["review_required"])
        self.assertIn("Technical methodology", result["documents_required"])
        self.assertIn("Service delivery plan", result["documents_required"])

    def test_document_metadata_and_backward_compatibility(self):
        path = ROOT / "data/sample_tenders/tender_002.txt"
        metadata = extract_document(path)
        self.assertEqual(metadata.file_type, "txt")
        self.assertGreater(metadata.character_count, 100)
        self.assertEqual(len(metadata.sha256), 64)
        self.assertEqual(extract_text(path), metadata.text)

    def test_empty_text_is_rejected(self):
        with self.assertRaises(ValueError):
            TenderRequirementAgent().extract("  ")


if __name__ == "__main__":
    unittest.main()
