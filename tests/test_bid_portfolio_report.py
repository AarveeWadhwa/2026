import tempfile
import unittest
from pathlib import Path
from backend.services.bid_portfolio_report import BidPortfolioReport


class BidPortfolioReportTests(unittest.TestCase):
    def setUp(self):
        self.workspace = {
            "agent": "member3_bid_workspace_pipeline",
            "results": [
                {"tender_id": "T-2", "analysis": {"recommendation": "REVIEW", "risk_level": "MEDIUM", "readiness_score": 72},
                 "change_report": {"changes": [{"field": "deadline"}]},
                 "preparation_checklist": {"items": [{"document": "OEM letter", "status": "MISSING"}]}},
                {"tender_id": "T-1", "analysis": {"recommendation": "NO_BID", "risk_level": "HIGH"},
                 "preparation_checklist": []}
            ]
        }

    def test_builds_action_register_and_counts(self):
        report = BidPortfolioReport().build(self.workspace)
        self.assertEqual(report["tender_count"], 2)
        self.assertEqual(report["recommendation_counts"]["REVIEW"], 1)
        row = next(x for x in report["action_register"] if x["tender_id"] == "T-2")
        self.assertEqual(row["action_count"], 1)
        self.assertEqual(row["change_count"], 1)
        self.assertTrue(report["human_review_required"])

    def test_handles_empty_results(self):
        report = BidPortfolioReport().build({"results": []})
        self.assertEqual(report["tender_count"], 0)
        self.assertEqual(report["action_register"], [])

    def test_rejects_non_list_results(self):
        with self.assertRaises(ValueError):
            BidPortfolioReport().build({"results": {}})

    def test_writes_csv_and_markdown(self):
        report = BidPortfolioReport().build(self.workspace)
        with tempfile.TemporaryDirectory() as temp:
            csv_path = Path(temp) / "report.csv"
            md_path = Path(temp) / "report.md"
            BidPortfolioReport.write_csv(report, csv_path)
            BidPortfolioReport.write_markdown(report, md_path)
            self.assertIn("tender_id", csv_path.read_text())
            self.assertIn("Bid Portfolio Summary", md_path.read_text())


if __name__ == "__main__":
    unittest.main()
