
import unittest
from backend.agents.compliance_agent import ComplianceAgent


class ComplianceTests(unittest.TestCase):
    def test_document_aliases_are_matched(self):
        company = {
            "company_name": "Example Co",
            "available_documents": ["PAN.pdf", "GST Registration Certificate.pdf", "ISO Certificate.pdf"],
        }
        result = ComplianceAgent().evaluate(
            ["PAN card", "GST certificate", "ISO certificate", "OEM authorization"],
            company,
        )
        self.assertEqual(result["available_count"], 3)
        self.assertEqual(result["missing_count"], 1)
        self.assertEqual(result["checklist"][-1]["status"], "MISSING")

    def test_empty_requirements_has_no_score(self):
        result = ComplianceAgent().evaluate([], {"company_name": "Example Co"})
        self.assertIsNone(result["document_readiness_score"])


if __name__ == "__main__":
    unittest.main()
