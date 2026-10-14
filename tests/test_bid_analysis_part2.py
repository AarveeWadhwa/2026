import unittest
from backend.agents.bid_analysis_agent import BidAnalysisAgent
from backend.agents.preparation_agent import PreparationAgent

class BidAnalysisPartTwoTests(unittest.TestCase):
    def test_reports_missing_documents_and_unknowns(self):
        report = BidAnalysisAgent().analyze(
            {"outcome": "NEEDS_REVIEW", "eligibility_score": None,
             "unknown_checks": [{"key": "turnover"}],
             "checks": [{"requirement": "Turnover", "status": "UNKNOWN", "explanation": "Not provided."}]},
            {"missing_count": 1, "checklist": [{"required_document": "PAN", "status": "MISSING", "action": "Upload PAN."}]},
            {"tender_id": "T-1"})
        self.assertEqual(report["readiness_status"], "NOT_READY_OR_REVIEW_REQUIRED")
        self.assertTrue(any("Required document missing" in risk for risk in report["risks"]))

    def test_preparation_checklist_contains_risk_actions(self):
        checklist = PreparationAgent().prepare("T-1",
            {"action_items": [{"priority": "HIGH", "action": "Obtain missing PAN."}]},
            {"checklist": [{"required_document": "PAN", "status": "MISSING"}]},
            deadline="2026-11-01")
        self.assertTrue(any("Obtain missing PAN" in x["task"] for x in checklist["items"]))
        self.assertTrue(any("Obtain and verify: PAN" in x["task"] for x in checklist["items"]))

if __name__ == "__main__": unittest.main()
