import tempfile
import unittest
from pathlib import Path
from backend.services.action_register import ActionRegister

class ActionRegisterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ActionRegister(Path(self.tmp.name) / 'memory.sqlite3')
        self.company = {'company_name':'Test Co','industry':'IT','location':'Pune'}
    def tearDown(self): self.tmp.cleanup()
    def test_manual_task_persists_and_update_is_audited(self):
        task = self.store.create(self.company, {'title':'Get signed certificate','agent_key':'manual','priority':'high','assignee':'Asha'})
        self.assertEqual(task['status'],'open')
        updated = self.store.update(self.company, task['task_id'], {'status':'in_progress','notes':'Asked finance team'})
        self.assertEqual(updated['status'],'in_progress')
        self.assertEqual(updated['notes'],'Asked finance team')
        events = self.store.events(self.company, task['task_id'])
        self.assertEqual(len(events),2)
        self.assertEqual(events[0]['event_type'],'updated')
    def test_agent_sync_is_idempotent_and_preserves_user_status(self):
        discovery={'results':[{'tender_id':'T-1','discovery':{'tender_id':'T-1','title':'Tender One'}}]}
        assessment={'results':[]}; workspace={'results':[]}
        first=self.store.sync_agent_outputs(self.company,discovery,assessment,workspace)
        self.assertGreaterEqual(first['generated_or_refreshed'],2)
        task=self.store.list(self.company)['tasks'][0]
        self.store.update(self.company,task['task_id'],{'status':'done','assignee':'Asha'})
        self.store.sync_agent_outputs(self.company,discovery,assessment,workspace)
        items=self.store.list(self.company)['tasks']
        same=next(x for x in items if x['task_id']==task['task_id'])
        self.assertEqual(same['status'],'done')
        self.assertEqual(same['assignee'],'Asha')
        self.assertEqual(len(items),first['generated_or_refreshed'])
    def test_company_scope_isolated(self):
        self.store.create(self.company, {'title':'Private task'})
        other={'company_name':'Other Co','industry':'IT','location':'Pune'}
        self.assertEqual(self.store.list(other)['count'],0)

if __name__=='__main__': unittest.main()
