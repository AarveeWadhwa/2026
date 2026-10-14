import unittest
from datetime import date
from backend.services.tender_quality import assess_tender, validate_envelope

class TenderQualityTests(unittest.TestCase):
    def test_complete_record_passes(self):
        record = {"tender_id":"T-1", "eligibility":{"minimum_turnover":"INR 1"}, "technical_requirements":["spec"], "financial_requirements":[{"type":"EMD","value":"0"}], "documents_required":["PAN"], "deadlines":{"bid_submission_deadline":"2030-01-01"}, "normalized_requirements":{"bid_submission_deadline_iso":"2030-01-01"}, "evidence":{"minimum_turnover":[{"quote":"turnover"}]}}
        result = assess_tender(record, today=date(2026, 1, 1))
        self.assertEqual(result["quality_status"], "checks_passed")
        self.assertEqual(result["completeness_score"], 100)
    def test_missing_fields_are_flagged(self):
        result = assess_tender({"tender_id":"T-2"}, today=date(2026, 1, 1))
        self.assertEqual(result["quality_status"], "needs_review")
        self.assertGreater(result["error_count"], 0)
    def test_past_deadline_is_flagged(self):
        record = {"tender_id":"T-3", "eligibility":{"x":1}, "technical_requirements":["x"], "financial_requirements":["x"], "documents_required":["x"], "deadlines":{"x":"2020-01-01"}, "normalized_requirements":{"bid_submission_deadline_iso":"2020-01-01"}, "evidence":{"x":[]}}
        result = assess_tender(record, today=date(2026, 1, 1))
        self.assertIn("deadline_passed", {i["code"] for i in result["issues"]})
    def test_bad_envelope_shape_raises(self):
        with self.assertRaises(ValueError):
            validate_envelope({"results":"not-an-array"})
    def test_envelope_counts(self):
        result = validate_envelope({"agent":"member1_tender_intelligence", "results":[{"tender_id":"T-1"}]}, today=date(2026,1,1))
        self.assertEqual(result["audited_count"], 1)
        self.assertEqual(result["needs_review_count"], 1)

if __name__ == "__main__":
    unittest.main()
