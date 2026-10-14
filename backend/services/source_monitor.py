"""Configurable HTTP source polling with persistent change detection.

Sources must be configured in data/monitor_sources.json. This generic adapter
monitors publicly accessible RSS, JSON, or HTML endpoints by content fingerprint.
Portal-specific extraction still requires a validated source adapter.
"""
from __future__ import annotations
import hashlib, json, sqlite3, time
from backend.services.db import connect, postgres_enabled
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse

class SourceMonitor:
    def __init__(self, db_path: str | Path, config_path: str | Path):
        self.db_path, self.config_path = (Path(db_path) if not postgres_enabled() else Path('.')), Path(config_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with connect(self.db_path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS monitored_sources (
                source_id TEXT PRIMARY KEY, url TEXT NOT NULL, content_hash TEXT NOT NULL,
                etag TEXT, last_modified TEXT, last_checked_at TEXT NOT NULL, last_status TEXT NOT NULL,
                last_change_json TEXT NOT NULL DEFAULT '{}')''')
            db.execute('''CREATE TABLE IF NOT EXISTS monitor_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL,
                url TEXT NOT NULL, event_type TEXT NOT NULL, old_hash TEXT, new_hash TEXT,
                observed_at TEXT NOT NULL, summary TEXT NOT NULL)''')

    def sources(self) -> list[dict[str, Any]]:
        if not self.config_path.exists(): return []
        data = json.loads(self.config_path.read_text(encoding='utf-8'))
        return data.get('sources', []) if isinstance(data, dict) else []

    @staticmethod
    def _fetch(source: dict[str, Any]) -> tuple[bytes, str | None, str | None, int]:
        url = str(source.get('url', '')).strip(); parsed = urlparse(url)
        if parsed.scheme != 'https' or not parsed.netloc:
            raise ValueError('Monitor sources must use an absolute HTTPS URL')
        headers = {'User-Agent': 'BidPilotAI/1.0 (configured tender source monitor)', 'Accept': 'application/json, application/rss+xml, application/atom+xml, text/html;q=0.9, */*;q=0.5'}
        request = Request(url, headers=headers)
        with urlopen(request, timeout=min(max(int(source.get('timeout_seconds', 15)), 3), 30)) as response:
            body = response.read(2_000_000)
            return body, response.headers.get('ETag'), response.headers.get('Last-Modified'), response.status

    def run_once(self, fetcher=None) -> dict[str, Any]:
        fetcher = fetcher or self._fetch; outcomes=[]; now=datetime.now(timezone.utc).isoformat()
        for source in self.sources():
            if not source.get('enabled', True): continue
            sid = str(source.get('id') or '').strip(); url = str(source.get('url') or '').strip()
            if not sid or not url:
                outcomes.append({'source_id': sid or None, 'status':'error','error':'Each source needs id and url'}); continue
            try:
                body, etag, modified, status = fetcher(source)
                digest = hashlib.sha256(body).hexdigest()
                with connect(self.db_path) as db:
                    previous = db.execute('SELECT content_hash FROM monitored_sources WHERE source_id=?', (sid,)).fetchone()
                    old_hash = (previous['content_hash'] if postgres_enabled() else previous[0]) if previous else None
                    event = 'baseline' if old_hash is None else ('changed' if old_hash != digest else 'unchanged')
                    db.execute('''INSERT INTO monitored_sources(source_id,url,content_hash,etag,last_modified,last_checked_at,last_status,last_change_json)
                        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET url=excluded.url,content_hash=excluded.content_hash,
                        etag=excluded.etag,last_modified=excluded.last_modified,last_checked_at=excluded.last_checked_at,last_status=excluded.last_status,
                        last_change_json=excluded.last_change_json''', (sid,url,digest,etag,modified,now,str(status),json.dumps({'event':event})))
                    if event == 'changed':
                        db.execute('INSERT INTO monitor_events(source_id,url,event_type,old_hash,new_hash,observed_at,summary) VALUES(?,?,?,?,?,?,?)',
                            (sid,url,event,old_hash,digest,now,'Source content changed. Re-fetch and re-parse tender details; rerun affected assessment stages.'))
                outcomes.append({'source_id':sid,'url':url,'status':'ok','event':event,'content_hash':digest,'http_status':status,
                                 'replan_required': event == 'changed', 'next_action':'run source-specific parser and re-assess affected tenders' if event=='changed' else None})
            except (ValueError, URLError, HTTPError, TimeoutError, OSError, Exception) as exc:
                outcomes.append({'source_id':sid,'url':url,'status':'error','error':str(exc)[:300]})
        return {'checked_at':now,'configured_sources':len(self.sources()),'checked_count':len(outcomes),
                'changed_count':sum(1 for x in outcomes if x.get('event')=='changed'),'results':outcomes,
                'note':'Content change detection is generic. A source-specific parser is required to extract corrigendum fields and automatically rerun affected tender agents.'}

    def status(self) -> dict[str, Any]:
        with connect(self.db_path) as db:
            rows=db.execute('SELECT source_id,url,content_hash,last_checked_at,last_status,last_change_json FROM monitored_sources ORDER BY source_id').fetchall()
            events=db.execute('SELECT event_id,source_id,url,event_type,observed_at,summary FROM monitor_events ORDER BY event_id DESC LIMIT 50').fetchall()
        return {'sources':[dict(r) for r in rows], 'recent_events':[dict(r) for r in events], 'configured_sources':len(self.sources())}
