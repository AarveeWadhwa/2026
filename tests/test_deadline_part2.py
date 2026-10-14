import unittest
from backend.agents.deadline_agent import DeadlineAgent
from backend.services.notification_service import NotificationService

class DeadlinePartTwoTests(unittest.TestCase):
    def test_detects_deadline_and_corrigendum_changes(self):
        report = DeadlineAgent().compare_snapshots(
            {"tender_id": "T-9", "deadline": "2026-11-01", "corrigendum": 0},
            {"tender_id": "T-9", "deadline": "2026-11-05", "corrigendum": 1})
        self.assertEqual(report["change_count"], 2)
        self.assertEqual(report["high_priority_count"], 2)
        self.assertEqual({x["field"] for x in report["changes"]}, {"deadline", "corrigendum"})

    def test_notification_payload_for_high_priority_change(self):
        report = DeadlineAgent().compare_snapshots(
            {"tender_id": "T-10", "deadline": "2026-11-01"},
            {"tender_id": "T-10", "deadline": "2026-11-02"})
        notifications = NotificationService().build_change_notifications(report)
        self.assertEqual(len(notifications), 1)
        self.assertTrue(notifications[0]["requires_delivery_adapter"])

if __name__ == "__main__": unittest.main()
