import unittest
from backend.agents.compliance_agent import ComplianceAgent

class CompliancePartTwoTests(unittest.TestCase):
    def test_missing_document_report(self):
        result = ComplianceAgent().evaluate(["PAN card", "OEM authorization"], {
            "company_name": "Demo", "available_documents": ["PAN.pdf"]
        })
        self.assertEqual(result["missing_count"], 1)
        self.assertEqual(result["checklist"][1]["status"], "MISSING")

    def test_document_inventory_metadata_is_preserved(self):
        result = ComplianceAgent().evaluate(["GST certificate"], {
            "company_name": "Demo",
            "available_documents": [{"name": "GST Registration Certificate.pdf",
                                     "status": "VALID", "expiry_date": "2027-01-01",
                                     "source": "company-upload"}]
        })
        self.assertEqual(result["checklist"][0]["status"], "AVAILABLE_MARKED_VALID")
        self.assertEqual(result["checklist"][0]["matched_company_documents"][0]["expiry_date"], "2027-01-01")

if __name__ == "__main__": unittest.main()
