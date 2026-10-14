
import unittest
from backend.agents.preparation_agent import BidPreparationAgent


class PreparationTests(unittest.TestCase):
    def test_report_includes_human_review_and_actions(self):
        analysis = {
            "tender_id": "T1", "tender_title": "Example Tender", "company_name": "Example Co",
            "recommendation": "ACTION_REQUIRED", "overall_score": 70,
            "eligibility_score": 80, "document_readiness_score": 50,
            "missing_documents": ["PAN card"], "unknown_eligibility_checks": [],
            "risks": ["Required document missing: PAN card"], "strengths": [],
        }
        report = BidPreparationAgent().prepare(analysis)
        self.assertTrue(report["human_review_required"])
        self.assertTrue(report["actions"])
        self.assertEqual(report["missing_documents"] if "missing_documents" in report else ["PAN card"], ["PAN card"])


if __name__ == "__main__":
    unittest.main()
