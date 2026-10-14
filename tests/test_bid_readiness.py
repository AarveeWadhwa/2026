import unittest
from backend.agents.bid_readiness_agent import BidReadinessAgent

class BidReadinessTests(unittest.TestCase):
    def test_combines_eligibility_and_compliance(self):
        result = BidReadinessAgent().evaluate(
            {"company_name": "Demo", "annual_turnover_inr": 20000000,
             "years_experience": 5, "location": "Pune, Maharashtra",
             "certifications": ["ISO 9001"], "available_documents": ["PAN.pdf"]},
            {"tender_id": "T-3", "normalized_requirements": {
                "minimum_turnover_inr": 10000000, "minimum_experience_years": 3,
                "location_requirement": "Maharashtra", "certifications": ["ISO 9001"],
                "documents_required": ["PAN card", "OEM authorization"]
            }}
        )
        self.assertEqual(result["overall_status"], "NOT_READY_OR_INCOMPLETE")
        self.assertEqual(result["compliance"]["missing_count"], 1)
        self.assertTrue(result["human_review_required"])

if __name__ == "__main__": unittest.main()
