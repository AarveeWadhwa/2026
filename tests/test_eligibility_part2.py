import unittest
from backend.agents.eligibility_agent import EligibilityAgent
from backend.models.tender import TenderRequirements

class EligibilityPartTwoTests(unittest.TestCase):
    def test_accepts_member1_normalized_output(self):
        extracted = {
            "tender_id": "T-42",
            "normalized_requirements": {
                "minimum_turnover_inr": 5000000,
                "minimum_experience_years": 3,
                "emd_inr": 100000,
                "tender_fee_inr": 2500,
                "deadline": "2026-11-01",
                "documents_required": ["PAN card"],
                "evidence": {"minimum_turnover": {"snippet": "Turnover at least ₹50 lakh"}},
                "review_required": True,
                "warnings": ["Verify the source clause"],
            },
        }
        tender = TenderRequirements.from_extraction(extracted)
        self.assertEqual(tender.minimum_turnover_inr, 5000000)
        self.assertEqual(tender.minimum_experience_years, 3)
        self.assertEqual(tender.emd_inr, 100000)
        self.assertEqual(tender.documents_required, ["PAN card"])
        self.assertTrue(tender.review_required)

    def test_missing_values_remain_unknown(self):
        result = EligibilityAgent().evaluate({"company_name": "Demo"}, {"tender_id": "T-1"})
        self.assertEqual(result["outcome"], "NEEDS_REVIEW")
        self.assertTrue(all(c["status"] == "UNKNOWN" for c in result["checks"][:3]))

    def test_includes_evidence_and_financial_obligations(self):
        tender = TenderRequirements.from_extraction({
            "tender_id": "T-2",
            "normalized_requirements": {
                "minimum_turnover_inr": 100,
                "evidence": {"minimum_turnover": {"snippet": "minimum turnover INR 100"}},
                "emd_inr": 50, "tender_fee_inr": 10, "deadline": "2026-12-01"
            }
        })
        result = EligibilityAgent().evaluate({"company_name": "Demo", "annual_turnover_inr": 200}, tender)
        self.assertEqual(result["checks"][0]["status"], "PASS")
        self.assertEqual(result["checks"][0]["evidence"]["snippet"], "minimum turnover INR 100")
        self.assertEqual(result["financial_obligations"]["emd_inr"], 50)

if __name__ == "__main__": unittest.main()
