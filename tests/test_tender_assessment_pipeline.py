import unittest
from backend.services.tender_assessment_pipeline import TenderAssessmentPipeline

class TenderAssessmentPipelineTests(unittest.TestCase):
    def setUp(self):
        self.company = {
            "company_name": "Aarav Systems",
            "industry": "IT services",
            "location": "Maharashtra",
            "annual_turnover_inr": 12000000,
            "years_experience": 5,
            "certifications": ["ISO 9001"],
            "available_documents": ["PAN card.pdf", "GST Registration Certificate.pdf"],
            "keywords": ["IT", "networking"],
        }

    def test_assesses_member1_part3_envelope(self):
        payload = {
            "schema_version": "1.0",
            "agent": "member1_tender_intelligence",
            "catalogue_mode": "local_catalogue",
            "result_count": 1,
            "results": [{
                "tender_id": "T-101",
                "normalized_requirements": {
                    "minimum_turnover_inr": 10000000,
                    "minimum_experience_years": 3,
                    "location_requirement": "Maharashtra",
                    "certifications": ["ISO 9001"],
                    "documents_required": ["PAN card", "GST certificate"],
                    "evidence": {"minimum_turnover": {"snippet": "Turnover >= ₹1 crore"}},
                },
                "evidence": {"minimum_turnover": {"snippet": "Turnover >= ₹1 crore"}},
                "warnings": [],
                "discovery": {"title": "IT Network Upgrade", "relevance_score": 0.8},
            }],
        }
        result = TenderAssessmentPipeline().assess(self.company, payload)
        self.assertEqual(result["assessed_tender_count"], 1)
        assessment = result["results"][0]
        self.assertEqual(assessment["tender_id"], "T-101")
        self.assertEqual(assessment["discovery"]["title"], "IT Network Upgrade")
        self.assertEqual(assessment["overall_status"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(assessment["eligibility"]["checks"][0]["status"], "PASS")

    def test_deadline_mismatch_becomes_action_item(self):
        payload = {"results": [{
            "tender_id": "T-102",
            "normalized_requirements": {"documents_required": []},
            "cross_checks": {"catalogue_vs_document_deadline": {
                "catalogue_deadline": "2026-11-01",
                "document_deadline": "2026-11-10",
                "status": "review_required"
            }},
        }]}
        result = TenderAssessmentPipeline().assess(self.company, payload)
        assessment = result["results"][0]
        self.assertEqual(assessment["overall_status"], "REVIEW_REQUIRED_DEADLINE_CROSS_CHECK")
        self.assertTrue(any(x["type"] == "DEADLINE_CROSS_CHECK" for x in assessment["action_items"]))

    def test_missing_document_extraction_is_not_silently_treated_as_success(self):
        payload = {"results": [{
            "tender_id": "T-103",
            "source_document": "data/sample_tenders/missing.txt",
            "warnings": ["Tender document not found"],
            "discovery": {"title": "Unknown tender"},
        }]}
        result = TenderAssessmentPipeline().assess(self.company, payload)
        assessment = result["results"][0]
        self.assertTrue(assessment["human_review_required"])
        self.assertTrue(any(x["type"] == "SOURCE_DOCUMENT" for x in assessment["action_items"]))

    def test_invalid_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            TenderAssessmentPipeline().assess(self.company, {"foo": "bar"})

if __name__ == "__main__":
    unittest.main()
