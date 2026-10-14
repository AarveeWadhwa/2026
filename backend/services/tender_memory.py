"""Persistent, company-scoped memory for repeated tender assessment cycles.

Uses SQLite from the Python standard library. Stores normalized tender snapshots and
assessment summaries only; source documents and secrets are never stored here.
"""
from __future__ import annotations
import hashlib
from contextlib import contextmanager
import json
import sqlite3
from pathlib import Path
from typing import Any
from datetime import datetime, timezone


class TenderMemoryStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS tender_cycles (
                company_key TEXT NOT NULL,
                tender_id TEXT NOT NULL,
                company_name TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                assessment_json TEXT NOT NULL,
                cycle_count INTEGER NOT NULL DEFAULT 1,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                PRIMARY KEY(company_key, tender_id)
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tender_cycles_company ON tender_cycles(company_key)")

    @staticmethod
    def company_key(company: dict[str, Any]) -> str:
        # Avoid raw company names in the database key while keeping a stable company-scoped history.
        identity = "|".join(str(company.get(k) or "").strip().casefold() for k in ("company_name", "industry", "location"))
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def get_company_history(self, company: dict[str, Any]) -> dict[str, dict[str, Any]]:
        key = self.company_key(company)
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM tender_cycles WHERE company_key=?", (key,)).fetchall()
        return {row["tender_id"]: {
            "snapshot": json.loads(row["snapshot_json"]),
            "assessment": json.loads(row["assessment_json"]),
            "cycle_count": row["cycle_count"],
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"],
        } for row in rows}

    def record_cycle(self, company: dict[str, Any], tender_id: str,
                     snapshot: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
        key = self.company_key(company)
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            old = conn.execute("SELECT cycle_count, first_seen_at FROM tender_cycles WHERE company_key=? AND tender_id=?", (key, tender_id)).fetchone()
            count = (old["cycle_count"] + 1) if old else 1
            first_seen = old["first_seen_at"] if old else now
            conn.execute("""INSERT INTO tender_cycles
                (company_key,tender_id,company_name,snapshot_json,assessment_json,cycle_count,first_seen_at,last_seen_at)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(company_key,tender_id) DO UPDATE SET
                company_name=excluded.company_name, snapshot_json=excluded.snapshot_json,
                assessment_json=excluded.assessment_json, cycle_count=excluded.cycle_count,
                last_seen_at=excluded.last_seen_at""",
                (key, tender_id, str(company.get("company_name") or "Company"),
                 json.dumps(snapshot, sort_keys=True), json.dumps(assessment, sort_keys=True), count, first_seen, now))
        return {"tender_id": tender_id, "cycle_count": count, "first_seen_at": first_seen, "last_seen_at": now}

    def clear_company(self, company: dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM tender_cycles WHERE company_key=?", (self.company_key(company),))
            return cur.rowcount
