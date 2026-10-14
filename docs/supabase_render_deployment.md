# Supabase + Render deployment

## Storage mode

BidPilot keeps local SQLite behavior when `DATABASE_URL` is absent. When
`DATABASE_URL` is set, the memory, preference, source-monitoring, and Action
Register services use PostgreSQL through psycopg 3. This code initializes its
tables at application startup; no Supabase service-role key is needed for direct
PostgreSQL connections.

## Supabase setup

1. In Supabase, open **Connect** and copy a PostgreSQL connection URI. Prefer
   the Session Pooler URI when deploying from a hosted service.
2. Keep the password private. Never commit the URI to Git.
3. In Render, add an environment variable named `DATABASE_URL` with that URI.
4. Ensure the URI's password is URL-encoded if it contains reserved characters.

## Render settings

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
- Use a free web service for a demo; it may sleep when idle.

## Important limitations

- This switches persistence to PostgreSQL for new data. It does not automatically
  migrate records from an existing local SQLite database. Export/import is needed
  if local tasks/history must be retained.
- Use a dedicated Supabase project/database and do not expose `DATABASE_URL`.
- The default tender catalogue remains local sample data; this change does not
  add live tender scraping.
- Run the test suite and verify `/api/health`, `/api/run`, `/api/actions`, and
  `/api/memory` after deployment. A PostgreSQL smoke test requires a reachable
  Supabase database and a private `DATABASE_URL`.
