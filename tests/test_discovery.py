
import unittest
from backend.agents.discovery_agent import TenderDiscoveryAgent


class DiscoveryTests(unittest.TestCase):
    def test_matching_tender_is_ranked(self):
        profile = {
            "industry": "IT",
            "services": "computer hardware networking",
            "keywords": ["laptops"],
            "location": "Maharashtra",
        }
        results = TenderDiscoveryAgent().search(profile)
        self.assertTrue(results)
        self.assertEqual(results[0]["tender_id"], "BP-2026-001")
        self.assertGreater(results[0]["relevance_score"], 0)
        self.assertIn("matched_terms", results[0])

    def test_empty_profile_returns_empty(self):
        self.assertEqual(TenderDiscoveryAgent().search({}), [])


if __name__ == "__main__":
    unittest.main()
