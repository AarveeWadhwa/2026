import json, tempfile, unittest
from pathlib import Path
from backend.services.source_monitor import SourceMonitor

class SourceMonitorTests(unittest.TestCase):
    def test_baseline_then_detects_content_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cfg=root/'sources.json'; cfg.write_text(json.dumps({'sources':[{'id':'official-test','url':'https://example.gov.in/tenders.json'}]}))
            monitor=SourceMonitor(root/'state.sqlite',cfg)
            first=monitor.run_once(fetcher=lambda source:(b'v1',None,None,200))
            second=monitor.run_once(fetcher=lambda source:(b'v2',None,None,200))
            third=monitor.run_once(fetcher=lambda source:(b'v2',None,None,200))
            self.assertEqual(first['results'][0]['event'],'baseline')
            self.assertTrue(second['results'][0]['replan_required'])
            self.assertEqual(third['results'][0]['event'],'unchanged')
            self.assertEqual(len(monitor.status()['recent_events']),1)

    def test_rejects_non_https_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cfg=root/'sources.json'; cfg.write_text(json.dumps({'sources':[{'id':'bad','url':'http://example.com'}]}))
            monitor=SourceMonitor(root/'state.sqlite',cfg)
            result=monitor.run_once()
            self.assertEqual(result['results'][0]['status'],'error')
