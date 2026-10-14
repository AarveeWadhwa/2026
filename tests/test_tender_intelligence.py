import json
import tempfile
import unittest
from pathlib import Path

from backend.agents.tender_intelligence_agent import TenderIntelligenceAgent, _safe_document_path


class TenderIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.profile = {
            "industry": "IT computer equipment",
            "services": "laptop network support",
            "keywords": ["laptop", "network", "hardware"],
            "location": "Maharashtra",
        }

    def test_discovery_and_extraction_are_combined(self):
        agent = TenderIntelligenceAgent(root=self.root)
        result = agent.run(self.profile, limit=4)
        self.assertEqual(result["agent"], "member1_tender_intelligence")
        self.assertGreater(result["result_count"], 0)
        tender = result["results"][0]
        self.assertIn("discovery", tender)
        self.assertIn("eligibility", tender)
        self.assertIn("normalized_requirements", tender)
        self.assertIn("evidence", tender)
        self.assertTrue(tender["review_required"])

    def test_result_has_member2_compatible_fields(self):
        result = TenderIntelligenceAgent(root=self.root).run(self.profile, limit=1)
        tender = result["results"][0]
        for field in ("tender_id", "eligibility", "certifications", "documents_required", "normalized_requirements"):
            self.assertIn(field, tender)

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            with self.assertRaises(ValueError):
                _safe_document_path("../outside.txt", root)

    def test_empty_profile_returns_no_results(self):
        result = TenderIntelligenceAgent(root=self.root).run({}, limit=4)
        self.assertEqual(result["result_count"], 0)
        self.assertEqual(result["results"], [])


if __name__ == "__main__":
    unittest.main()
