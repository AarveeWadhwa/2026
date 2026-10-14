
import unittest
from backend.agents.bid_analysis_agent import BidAnalysisAgent


class BidAnalysisTests(unittest.TestCase):
    def test_missing_document_requires_action(self):
        eligibility = {
            "company_name": "Example Co", "tender_id": "T1", "eligibility_score": 100,
            "checks": [{"requirement": "Turnover", "status": "PASS"}],
            "failed_checks": [], "unknown_checks": [],
        }
        compliance = {
            "company_name": "Example Co", "document_readiness_score": 75,
            "checklist": [{"required_document": "OEM authorization", "status": "MISSING"}],
        }
        result = BidAnalysisAgent().analyze(eligibility, compliance, {"tender_id": "T1", "title": "Example"})
        self.assertEqual(result["recommendation"], "ACTION_REQUIRED")
        self.assertEqual(result["missing_documents"], ["OEM authorization"])


if __name__ == "__main__":
    unittest.main()
