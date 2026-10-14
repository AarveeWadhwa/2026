"""Company preference memory derived from explicit human feedback.

This is transparent feedback-based adaptation, not an opaque trained model. The
stored weights can be inspected, reset, and overridden by the company.
"""
from __future__ import annotations
import hashlib, json, sqlite3
from backend.services.db import connect, postgres_enabled
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

class PreferenceMemory:
    def __init__(self, path: str | Path):
        self.path = Path(path) if not postgres_enabled() else Path('.'); self.path.parent.mkdir(parents=True, exist_ok=True)
        with connect(self.path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS company_feedback (
                company_key TEXT NOT NULL, feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id TEXT, category TEXT NOT NULL, keywords_json TEXT NOT NULL,
                rating INTEGER NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL)''')

    @staticmethod
    def key(company: dict[str, Any]) -> str:
        value = '|'.join(str(company.get(k) or '').strip().casefold() for k in ('company_name','industry','location'))
        return hashlib.sha256(value.encode()).hexdigest()

    def record(self, company: dict[str, Any], category: str, keywords: list[str], rating: int, tender_id: str = '', note: str = '') -> dict[str, Any]:
        if rating not in (-1, 1): raise ValueError('rating must be 1 (useful) or -1 (not useful)')
        clean = list(dict.fromkeys(x.strip().lower() for x in keywords if x.strip()))[:30]
        now = datetime.now(timezone.utc).isoformat()
        with connect(self.path) as db:
            insert_sql = 'INSERT INTO company_feedback(company_key,tender_id,category,keywords_json,rating,note,created_at) VALUES(?,?,?,?,?,?,?)'
            params = (self.key(company), tender_id.strip(), category.strip().lower() or 'general', json.dumps(clean), rating, note[:500], now)
            if postgres_enabled():
                feedback_id = db.execute(insert_sql + ' RETURNING feedback_id', params).fetchone()['feedback_id']
            else:
                feedback_id = db.execute(insert_sql, params).lastrowid
        return {'feedback_id': feedback_id, 'category': category, 'keywords': clean, 'rating': rating, 'created_at': now}

    def profile(self, company: dict[str, Any]) -> dict[str, Any]:
        with connect(self.path) as db:
            rows = db.execute('SELECT category,keywords_json,rating,created_at FROM company_feedback WHERE company_key=? ORDER BY feedback_id', (self.key(company),)).fetchall()
        weights: dict[str, int] = {}; categories: dict[str, int] = {}
        for row in rows:
            category, encoded, rating, _ = (row['category'], row['keywords_json'], row['rating'], row['created_at']) if postgres_enabled() else row
            categories[category] = categories.get(category, 0) + rating
            for word in json.loads(encoded): weights[word] = weights.get(word, 0) + rating
        positive = sorted((w for w, n in weights.items() if n > 0), key=lambda w: (-weights[w], w))
        negative = sorted((w for w, n in weights.items() if n < 0), key=lambda w: (weights[w], w))
        return {'feedback_count': len(rows), 'keyword_weights': weights, 'preferred_keywords': positive,
                'deprioritized_keywords': negative, 'category_weights': categories,
                'adaptation': 'explicit_feedback_counts; human-editable; not model training'}
