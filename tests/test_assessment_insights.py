import unittest
from backend.services.assessment_insights import AssessmentInsights

class AssessmentInsightsTests(unittest.TestCase):
    def test_summarizes_status_actions_and_missing_documents(self):
        source = {"results": [{"tender_id":"T1", "overall_status":"NOT_READY_OR_INCOMPLETE", "human_review_required":True,
            "action_items":[{"priority":"HIGH","item":"GST","action":"Upload GST"}],
            "eligibility":{"eligibility_score":50}, "compliance":{"document_readiness_score":50,"checklist":[{"required_document":"GST certificate","status":"MISSING"}]}}]}
        result = AssessmentInsights().build(source)
        self.assertEqual(result["tender_count"], 1)
        self.assertEqual(result["high_priority_action_count"], 1)
        self.assertEqual(result["missing_document_count"], 1)
    def test_empty_assessment(self):
        result = AssessmentInsights().build({"results": []})
        self.assertEqual(result["tender_count"], 0)
    def test_invalid_results(self):
        with self.assertRaises(ValueError): AssessmentInsights().build({"results": {}})

if __name__ == "__main__": unittest.main()
