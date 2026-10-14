import unittest
from backend.services.bid_workspace_pipeline import BidWorkspacePipeline


class BidWorkspacePipelineTests(unittest.TestCase):
    def setUp(self):
        self.assessments = [{
            "tender_id": "BP-TEST-01",
            "tender": {"tender_id": "BP-TEST-01", "title": "IT equipment supply", "deadline": "2026-11-05"},
            "eligibility_result": {
                "company_name": "Example Systems", "eligibility_score": 70,
                "checks": [{"requirement": "Turnover", "status": "PASS", "evidence": "Audited accounts"}],
                "failed_checks": [], "unknown_checks": [],
            },
            "compliance_result": {
                "company_name": "Example Systems", "document_readiness_score": 50,
                "checklist": [
                    {"required_document": "GST certificate", "status": "AVAILABLE"},
                    {"required_document": "OEM authorization", "status": "MISSING", "action": "Request OEM letter"},
                ],
            },
        }]

    def test_builds_analysis_and_checklist(self):
        result = BidWorkspacePipeline().run(self.assessments)
        self.assertEqual(result["assessment_count"], 1)
        item = result["results"][0]
        self.assertEqual(item["tender_id"], "BP-TEST-01")
        self.assertIn("OEM authorization", item["analysis"]["missing_documents"])
        self.assertTrue(any("Request OEM letter" in x["task"] for x in item["preparation_checklist"]["items"]))
        self.assertTrue(result["human_review_required"])

    def test_detects_deadline_change_and_creates_alert_payload(self):
        current = [{"tender_id": "BP-TEST-01", "deadline": "2026-11-08", "emd": 50000}]
        previous = [{"tender_id": "BP-TEST-01", "deadline": "2026-11-05", "emd": 50000}]
        result = BidWorkspacePipeline().run(self.assessments, current, previous)
        item = result["results"][0]
        self.assertTrue(item["change_report"]["change_count"] >= 1)
        self.assertTrue(any(n["event"] == "TENDER_CHANGE" for n in item["notifications"]))

    def test_requires_tender_id(self):
        with self.assertRaises(ValueError):
            BidWorkspacePipeline().run([{"eligibility_result": {}, "compliance_result": {}}])

    def test_no_snapshots_means_no_change_report(self):
        result = BidWorkspacePipeline().run(self.assessments)
        self.assertIsNone(result["results"][0]["change_report"])
        self.assertEqual(result["notifications"], [])


if __name__ == "__main__":
    unittest.main()
