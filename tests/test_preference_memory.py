import tempfile, unittest
from pathlib import Path
from backend.services.preference_memory import PreferenceMemory

class PreferenceMemoryTests(unittest.TestCase):
    def test_feedback_changes_preference_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=PreferenceMemory(Path(tmp)/'m.sqlite')
            company={'company_name':'A','industry':'IT','location':'Pune'}
            store.record(company,'networking',['network','router'],1)
            store.record(company,'networking',['router','firewall'],-1)
            profile=store.profile(company)
            self.assertIn('network',profile['preferred_keywords'])
            self.assertIn('firewall',profile['deprioritized_keywords'])
            self.assertEqual(profile['feedback_count'],2)

    def test_company_feedback_is_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=PreferenceMemory(Path(tmp)/'m.sqlite')
            store.record({'company_name':'A','industry':'IT','location':'Pune'},'x',['cloud'],1)
            self.assertEqual(store.profile({'company_name':'B','industry':'IT','location':'Pune'})['feedback_count'],0)
