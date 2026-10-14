
import unittest
from backend.agents.eligibility_agent import EligibilityAgent


class EligibilityTests(unittest.TestCase):
    def test_passes_when_values_meet_requirements(self):
        company = {
            "company_name": "Example Co",
            "location": "Pune, Maharashtra",
            "annual_turnover_inr": 12_000_000,
            "years_experience": 5,
            "certifications": ["ISO 9001"],
        }
        tender = {
            "tender_id": "T-1",
            "minimum_turnover_inr": 10_000_000,
            "minimum_experience_years": 3,
            "location_requirement": "Maharashtra",
            "certifications": ["ISO 9001"],
        }
        result = EligibilityAgent().evaluate(company, tender)
        self.assertEqual(result["outcome"], "MEETS_CHECKED_CRITERIA")
        self.assertEqual(result["eligibility_score"], 100.0)

    def test_missing_data_is_unknown_not_fail(self):
        company = {"company_name": "Example Co"}
        tender = {"tender_id": "T-2", "minimum_turnover_inr": 10_000_000}
        result = EligibilityAgent().evaluate(company, tender)
        self.assertEqual(result["checks"][0]["status"], "UNKNOWN")
        self.assertIsNone(result["checks"][1]["required_value"])


if __name__ == "__main__":
    unittest.main()
