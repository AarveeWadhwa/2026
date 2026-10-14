"""Persistent task-management layer for agent-generated bid actions.

Tasks are company-scoped, idempotently refreshed from agent output, editable by
people, and audited in SQLite. It is a lightweight local task register, not a
replacement for a full project-management or notification platform.
"""
from __future__ import annotations
import hashlib, json, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENTS = {
    "tender_discovery": "Tender Discovery Agent",
    "requirement_extraction": "Requirement Extraction Agent",
    "eligibility": "Eligibility Agent",
    "compliance": "Compliance / Document Agent",
    "bid_analysis": "Bid Analysis Agent",
    "deadline_corrigendum": "Deadline & Corrigendum Agent",
    "bid_preparation": "Bid Preparation Agent",
    "replanning": "Replanning Engine",
    "manual": "User-created task",
}
STATUSES = {"open", "in_progress", "blocked", "done", "cancelled"}
PRIORITIES = {"low", "medium", "high", "urgent"}

class ActionRegister:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path); self.db_path.parent.mkdir(parents=True, exist_ok=True); self._init()

    @contextmanager
    def _db(self):
        con = sqlite3.connect(self.db_path); con.row_factory = sqlite3.Row
        try:
            yield con; con.commit()
        except Exception:
            con.rollback(); raise
        finally: con.close()

    def _init(self):
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS action_tasks (
                task_id TEXT PRIMARY KEY, company_key TEXT NOT NULL, company_name TEXT NOT NULL,
                tender_id TEXT NOT NULL DEFAULT '', tender_title TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', agent_key TEXT NOT NULL,
                source_key TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'medium', status TEXT NOT NULL DEFAULT 'open',
                assignee TEXT NOT NULL DEFAULT '', due_date TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
                dependencies_json TEXT NOT NULL DEFAULT '[]', replanning_cycle INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, completed_at TEXT NOT NULL DEFAULT '',
                UNIQUE(company_key, tender_id, agent_key, source_key))""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_action_tasks_company_status ON action_tasks(company_key,status,due_date)")
            c.execute("""CREATE TABLE IF NOT EXISTS action_task_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, company_key TEXT NOT NULL,
                event_type TEXT NOT NULL, old_json TEXT NOT NULL, new_json TEXT NOT NULL, created_at TEXT NOT NULL)""")

    @staticmethod
    def company_key(company: dict[str, Any]) -> str:
        identity = '|'.join(str(company.get(k) or '').strip().casefold() for k in ('company_name','industry','location'))
        return hashlib.sha256(identity.encode()).hexdigest()

    @staticmethod
    def _task_id(company_key: str, tid: str, agent: str, source: str) -> str:
        return hashlib.sha1(f'{company_key}|{tid}|{agent}|{source}'.encode()).hexdigest()[:16]

    def _upsert_generated(self, c, company, task):
        ck = self.company_key(company); tid = str(task.get('tender_id') or '')
        agent = task['agent_key']; source = str(task.get('source_key') or task['title']); priority = str(task.get('priority') or 'medium').lower()
        if priority not in PRIORITIES: priority = 'medium'
        task_id = self._task_id(ck, tid, agent, source); now = datetime.now(timezone.utc).isoformat()
        old = c.execute('SELECT * FROM action_tasks WHERE task_id=?', (task_id,)).fetchone()
        if old:
            # Refresh agent-derived context without overwriting user-managed fields.
            c.execute('''UPDATE action_tasks SET company_name=?, tender_title=?, title=?, description=?, priority=?,
                dependencies_json=?, replanning_cycle=?, updated_at=? WHERE task_id=?''',
                (company.get('company_name','Company'), task.get('tender_title',''), task['title'], task.get('description',''),
                 priority, json.dumps(task.get('dependencies',[])), int(task.get('replanning_cycle',0)), now, task_id))
        else:
            c.execute('''INSERT INTO action_tasks(task_id,company_key,company_name,tender_id,tender_title,title,description,
                agent_key,source_key,priority,status,dependencies_json,replanning_cycle,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?, 'open', ?, ?, ?, ?)''',
                (task_id,ck,company.get('company_name','Company'),tid,task.get('tender_title',''),task['title'],task.get('description',''),
                 agent,source,priority,json.dumps(task.get('dependencies',[])),int(task.get('replanning_cycle',0)),now,now))
            c.execute('INSERT INTO action_task_events(task_id,company_key,event_type,old_json,new_json,created_at) VALUES(?,?,?,?,?,?)',
                      (task_id,ck,'created','{}',json.dumps({'title':task['title'],'agent_key':agent}),now))

    def sync_agent_outputs(self, company: dict[str, Any], discovery: dict, assessment: dict, workspace: dict,
                           replanning: list[dict] | None = None, replanning_execution: list[dict] | None = None) -> dict:
        """Idempotently persist work items emitted by all seven agent roles."""
        tasks=[]; extracted={str(x.get('tender_id') or (x.get('discovery') or {}).get('tender_id') or ''):x for x in discovery.get('results',[])}
        assess={str(x.get('tender_id') or ''):x for x in assessment.get('results',[])}
        replans={str(x.get('tender_id') or ''):x for x in (replanning or [])}
        work={str(x.get('tender_id') or ''):x for x in workspace.get('results',[])}
        for tid,t in extracted.items():
            if not tid: continue
            d=t.get('discovery') or {}; title=d.get('title') or tid
            def add(agent, source, label, desc='', priority='medium', deps=None):
                tasks.append({'tender_id':tid,'tender_title':title,'agent_key':agent,'source_key':str(source), 'title':label,
                              'description':desc,'priority':priority,'dependencies':deps or [],
                              'replanning_cycle':1 if replans.get(tid,{}).get('replan_required') else 0})
            add('tender_discovery','verify_source',f'Verify official source for {title}',f"Confirm tender {tid} and its latest published documents from the official portal.",'high')
            req=t.get('normalized_requirements') or {}
            add('requirement_extraction','verify_extraction',f'Validate extracted requirements — {tid}',f"Check deadline, EMD, turnover, experience and technical fields against the source. Extracted deadline: {((t.get('deadlines') or {}).get('bid_submission_deadline') or d.get('catalogue_deadline') or 'not found')}.",'high',['tender_discovery'])
            ar=assess.get(tid,{})
            eligibility_task_start=len(tasks)
            for i,check in enumerate((ar.get('eligibility') or {}).get('checks',[]) or []):
                status=str(check.get('status','')).upper()
                if status not in ('PASS','ELIGIBLE','MET','AVAILABLE_MARKED_VALID'):
                    label=str(check.get('requirement') or check.get('key') or 'Eligibility check')
                    add('eligibility',f'check_{i}_{label}',f'Resolve eligibility check: {label}',str(check.get('explanation') or check.get('status') or 'Manual validation required.'),'high' if status in ('FAIL','INELIGIBLE') else 'medium',['requirement_extraction'])
            if len(tasks)==eligibility_task_start:
                add('eligibility','verify_assessment',f'Confirm eligibility assessment — {tid}','Review the eligibility outcome and evidence before making a bid/no-bid decision.','medium',['requirement_extraction'])
            compliance_task_start=len(tasks)
            for i,check in enumerate((ar.get('compliance') or {}).get('checklist',[]) or []):
                status=str(check.get('status','')).upper()
                if status not in ('AVAILABLE_MARKED_VALID','AVAILABLE','PASS','COMPLETE'):
                    doc=str(check.get('required_document') or check.get('document') or f'Document {i+1}')
                    add('compliance',f'doc_{i}_{doc}',f'Collect or verify document: {doc}',str(check.get('action') or 'Confirm validity, signatory and tender-specific format.'),'high' if status in ('MISSING','FAIL') else 'medium',['eligibility'])
            if len(tasks)==compliance_task_start:
                add('compliance','verify_document_set',f'Confirm document set — {tid}','Verify that each required document is current, signed where necessary, and in the tender-prescribed format.','medium',['eligibility'])
            w=work.get(tid,{})
            analysis=w.get('analysis') or {}
            analysis_task_start=len(tasks)
            for i,item in enumerate(analysis.get('action_items') or []):
                text=str(item.get('action') or item.get('item') or item.get('description') or 'Review bid analysis recommendation') if isinstance(item,dict) else str(item)
                pri=str((item.get('priority') if isinstance(item,dict) else 'medium') or 'medium').lower()
                add('bid_analysis',f'recommendation_{i}_{text}',text,str(item.get('reason') or '') if isinstance(item,dict) else '',pri,['eligibility','compliance'])
            if len(tasks)==analysis_task_start:
                add('bid_analysis','review_bid_readiness',f'Review bid/no-bid recommendation — {tid}','Check readiness signals, unresolved unknowns and commercial assumptions before deciding to proceed.','medium',['eligibility','compliance'])
            preparation_task_start=len(tasks)
            for i,item in enumerate((w.get('preparation_checklist') or {}).get('items',[]) or []):
                text=str(item.get('action') or item.get('task') or item.get('item') or item.get('document') or 'Prepare bid item') if isinstance(item,dict) else str(item)
                pri=str((item.get('priority') if isinstance(item,dict) else 'medium') or 'medium').lower()
                add('bid_preparation',f'checklist_{i}_{text}',text,'Generated by the bid preparation checklist.',pri,['compliance','bid_analysis'])
            if len(tasks)==preparation_task_start:
                add('bid_preparation','review_submission_pack',f'Validate submission pack — {tid}','Review the bid pack, portal submission steps, signatures and deadline buffer.','medium',['compliance','bid_analysis'])
            cr=w.get('change_report') or {}
            changes=cr.get('changes') or []
            if not changes:
                add('deadline_corrigendum','confirm_current_deadline_and_corrigenda',f'Confirm latest deadline and corrigenda — {tid}',
                    'Check the official portal for a newer corrigendum or deadline extension before acting on this task list. No change was detected in the currently available snapshots.','high',['requirement_extraction'])
            for i,change in enumerate(changes):
                field=str(change.get('field') or 'tender field'); detail=str(change.get('message') or change.get('description') or 'A snapshot difference was detected.')
                add('deadline_corrigendum',f'change_{i}_{field}',f'Review tender change: {field}',detail,'urgent' if str(change.get('severity','')).upper() in ('HIGH','CRITICAL') else 'high',['requirement_extraction'])
            rp=replans.get(tid,{})
            if rp.get('replan_required'):
                fields=', '.join(rp.get('changed_fields') or [])
                add('replanning',f'material_change_{fields}',f'Review replanned workflow for {tid}',f'Material change detected in: {fields}. Revisit: {", ".join(rp.get("steps_to_revisit") or [])}.','urgent',['requirement_extraction','eligibility','compliance','bid_analysis','bid_preparation'])
        # Persist even if a given agent emits no task for this cycle; existing human tasks remain.
        with self._db() as c:
            for task in tasks: self._upsert_generated(c,company,task)
        return {'generated_or_refreshed':len(tasks),'agent_roles_connected':sorted(set(t['agent_key'] for t in tasks)), 'persistent':True}

    def create(self, company: dict[str,Any], payload: dict[str,Any]) -> dict:
        title=str(payload.get('title') or '').strip()
        if not title: raise ValueError('Task title is required.')
        agent=str(payload.get('agent_key') or 'manual')
        if agent not in AGENTS: raise ValueError('Unknown agent role.')
        priority=str(payload.get('priority') or 'medium').lower(); status=str(payload.get('status') or 'open').lower()
        if priority not in PRIORITIES: raise ValueError('Invalid priority.')
        if status not in STATUSES: raise ValueError('Invalid status.')
        ck=self.company_key(company); tid=str(payload.get('tender_id') or '').strip(); source='manual_'+hashlib.sha1((title+datetime.now(timezone.utc).isoformat()).encode()).hexdigest()[:12]
        task_id=self._task_id(ck,tid,agent,source); now=datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute('''INSERT INTO action_tasks(task_id,company_key,company_name,tender_id,tender_title,title,description,agent_key,source_key,priority,status,assignee,due_date,notes,dependencies_json,replanning_cycle,created_at,updated_at,completed_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (task_id,ck,company.get('company_name','Company'),tid,str(payload.get('tender_title') or ''),title,str(payload.get('description') or ''),agent,source,priority,status,str(payload.get('assignee') or ''),str(payload.get('due_date') or ''),str(payload.get('notes') or ''),'[]',0,now,now,now if status=='done' else ''))
            c.execute('INSERT INTO action_task_events(task_id,company_key,event_type,old_json,new_json,created_at) VALUES(?,?,?,?,?,?)',(task_id,ck,'created','{}',json.dumps(payload),now))
        return self.get_one(company,task_id)

    def get_one(self, company, task_id):
        with self._db() as c: row=c.execute('SELECT * FROM action_tasks WHERE company_key=? AND task_id=?',(self.company_key(company),task_id)).fetchone()
        if not row: return None
        return self._serialize(row)

    @staticmethod
    def _serialize(row):
        d=dict(row); d['dependencies']=json.loads(d.pop('dependencies_json','[]')); d['agent_name']=AGENTS.get(d['agent_key'],d['agent_key']); return d

    def list(self, company, status='', tender_id='', agent_key=''):
        q='SELECT * FROM action_tasks WHERE company_key=?'; args=[self.company_key(company)]
        if status: q+=' AND status=?'; args.append(status)
        if tender_id: q+=' AND tender_id=?'; args.append(tender_id)
        if agent_key: q+=' AND agent_key=?'; args.append(agent_key)
        q+=' ORDER BY CASE priority WHEN "urgent" THEN 0 WHEN "high" THEN 1 WHEN "medium" THEN 2 ELSE 3 END, CASE status WHEN "done" THEN 1 ELSE 0 END, due_date, created_at DESC'
        with self._db() as c: rows=c.execute(q,args).fetchall()
        items=[self._serialize(r) for r in rows]
        return {'count':len(items),'tasks':items,'summary':{'open':sum(x['status']=='open' for x in items),'in_progress':sum(x['status']=='in_progress' for x in items),'blocked':sum(x['status']=='blocked' for x in items),'done':sum(x['status']=='done' for x in items),'cancelled':sum(x['status']=='cancelled' for x in items)}}

    def update(self, company, task_id, changes):
        allowed={'title','description','priority','status','assignee','due_date','notes'}
        unknown=set(changes)-allowed
        if unknown: raise ValueError('Fields cannot be changed: '+', '.join(sorted(unknown)))
        if 'title' in changes and not str(changes['title']).strip(): raise ValueError('Task title cannot be empty.')
        if 'priority' in changes and str(changes['priority']).lower() not in PRIORITIES: raise ValueError('Invalid priority.')
        if 'status' in changes and str(changes['status']).lower() not in STATUSES: raise ValueError('Invalid status.')
        ck=self.company_key(company); now=datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            row=c.execute('SELECT * FROM action_tasks WHERE company_key=? AND task_id=?',(ck,task_id)).fetchone()
            if not row: return None
            old=dict(row); merged={k:old[k] for k in allowed}; merged.update(changes)
            completed=now if merged['status']=='done' else ('' if old['status']=='done' else old['completed_at'])
            c.execute('''UPDATE action_tasks SET title=?,description=?,priority=?,status=?,assignee=?,due_date=?,notes=?,updated_at=?,completed_at=? WHERE company_key=? AND task_id=?''',
                (merged['title'],merged['description'],str(merged['priority']).lower(),str(merged['status']).lower(),merged['assignee'],merged['due_date'],merged['notes'],now,completed,ck,task_id))
            c.execute('INSERT INTO action_task_events(task_id,company_key,event_type,old_json,new_json,created_at) VALUES(?,?,?,?,?,?)',(task_id,ck,'updated',json.dumps({k:old[k] for k in changes}),json.dumps(changes),now))
        return self.get_one(company,task_id)

    def events(self, company, task_id=''):
        q='SELECT * FROM action_task_events WHERE company_key=?'; args=[self.company_key(company)]
        if task_id: q+=' AND task_id=?'; args.append(task_id)
        q+=' ORDER BY event_id DESC LIMIT 200'
        with self._db() as c: rows=c.execute(q,args).fetchall()
        out=[]
        for r in rows:
            x=dict(r); x['old']=json.loads(x.pop('old_json')); x['new']=json.loads(x.pop('new_json')); out.append(x)
        return out
