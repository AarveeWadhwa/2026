import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import app
import backend.app as app_module

class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.client = TestClient(app)
    def test_health_and_frontend(self):
        self.assertEqual(self.client.get('/api/health').status_code, 200)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('BidPilot AI', response.text)
    def test_end_to_end_pipeline(self):
        response = self.client.post('/api/run', json={})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreater(data['summary']['tenders_found'], 0)
        self.assertIn('assessment_insights', data)
        self.assertIn('portfolio', data)
        self.assertIn('replanning', data)
        self.assertIn('replanning_execution', data)
        self.assertTrue(data['memory']['enabled'])
    def test_material_change_executes_replanning_loop(self):
        previous_snapshot = {
            'tender_id': 'BP-2026-001', 'title': 'Supply and Installation of Computer Equipment',
            'deadline': '2026-11-05', 'emd': 1, 'documents_required': [], 'certifications': [],
            'eligibility': {'minimum_turnover': '₹1'}, 'minimum_turnover': 1,
            'minimum_experience': 1, 'technical_requirements': ['old requirement'], 'source_url': None,
        }
        fake_history = {'BP-2026-001': {
            'snapshot': previous_snapshot, 'assessment': {'overall_status': 'NOT_READY_OR_INCOMPLETE'},
            'cycle_count': 1, 'first_seen_at': '2026-10-01T00:00:00+00:00',
            'last_seen_at': '2026-10-01T00:00:00+00:00'
        }}
        with patch.object(app_module.MEMORY, 'get_company_history', return_value=fake_history):
            response = self.client.post('/api/run', json={})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        executions = data['replanning_execution']
        self.assertTrue(executions, 'material snapshot change should execute a replan cycle')
        self.assertEqual(executions[0]['status'], 'completed')
        self.assertIn('requirement_extraction', executions[0]['executed_stages'])
        self.assertIn('eligibility', executions[0]['executed_stages'])
        self.assertGreaterEqual(executions[0]['rerun_tender_count'], 1)

    def test_action_register_create_update_and_history(self):
        company = {'company_name':'Action API Test Co','industry':'IT services','location':'Pune'}
        created = self.client.post('/api/actions', json={'company':company,'title':'Collect signed certificate','priority':'high','assignee':'Reviewer'})
        self.assertEqual(created.status_code, 200, created.text)
        task = created.json()['task']
        self.assertEqual(task['status'], 'open')
        updated = self.client.patch('/api/actions/'+task['task_id'], json={'company':company,'status':'in_progress','notes':'Requested from finance'})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()['task']['status'], 'in_progress')
        history = self.client.get('/api/actions/'+task['task_id']+'/history', params=company)
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(len(history.json()['events']), 2)

    def test_invalid_company_returns_validation_error(self):
        response = self.client.post('/api/run', json={'company': {'company_name': ''}})
        self.assertEqual(response.status_code, 422)

if __name__ == '__main__': unittest.main()
