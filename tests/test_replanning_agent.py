import unittest
from backend.agents.replanning_agent import ReplanningAgent

class ReplanningAgentTests(unittest.TestCase):
    def setUp(self): self.agent = ReplanningAgent()
    def test_first_cycle_creates_baseline_without_change_alert(self):
        result = self.agent.plan(None, {"deadline": "2026-11-05"})
        self.assertFalse(result["replan_required"])
        self.assertEqual(result["memory_cycle"], "first_seen")
    def test_deadline_change_revisits_analysis_and_preparation(self):
        result = self.agent.plan({"deadline": "2026-11-05", "documents_required": []},
                                 {"deadline": "2026-11-10", "documents_required": []})
        self.assertTrue(result["replan_required"])
        self.assertIn("deadline", result["changed_fields"])
        self.assertIn("bid_preparation", result["steps_to_revisit"])
    def test_eligibility_change_revisits_eligibility_compliance(self):
        result = self.agent.plan({"minimum_turnover": 1000000}, {"minimum_turnover": 2000000})
        self.assertIn("eligibility", result["steps_to_revisit"])
        self.assertIn("compliance", result["steps_to_revisit"])
    def test_no_material_change_does_not_replan(self):
        snap = {"deadline": "2026-11-05", "emd": 50000}
        self.assertFalse(self.agent.plan(snap, dict(snap))["replan_required"])
