# Web registration rollout (SSR Jinja/HTMX)

## Phase 1 (current)

- Alembic revision `a9c1e2f3b4d5`: nullable `user.email`, `user.password_hash`, non-unique index `ix_user_email`.
- Web users get a **unique negative** `user_telegram_id` (Telegram IDs are positive); Telegram flow unchanged.
- Routes: `GET /register`, `POST /register` (HTMX partial `partials/register_result.html`).
- Static: `/web-static/style.css`.

### Dev

1. `poetry install`
2. Apply migrations: `poetry run alembic upgrade head`
3. Run the client bot process: **always** `uvicorn` on `TELEGRAM_WEB_HOST`:`TELEGRAM_WEB_PORT` (e.g. `python client_bot_run.py` or `uvicorn client_bot_run:app --host … --port …`). HTTP (`/health`, `/register`, …) is served in the same process. `POLLING_MODE=true` runs Telegram long polling as a **background task**; `POLLING_MODE=false` registers a webhook with Telegram (needs a public `WEBHOOK_URL`).
4. Open `/register`, submit form, verify row in `user` with `email`, `password_hash`, `user_telegram_id < 0`.

### Stage

1. Backup DB (snapshot or logical dump).
2. `alembic upgrade head` then deploy application.
3. Smoke: `/health`, `/ready`, `/register` (success + duplicate email + password mismatch).
4. Watch logs for DB errors during registration.

### Prod (phase 1)

1. Maintenance window optional (additive columns + index are usually online).
2. **Migrate first**, then deploy application (old code ignores new columns).
3. Smoke same as stage; monitor error rate after deploy.

### Rollback (phase 1)

- **App only:** deploy previous image; new columns remain unused (safe).
- **DB:** only if revision must be reverted — `alembic downgrade -1` after app rollback (drops columns; ensure no reliance on web users).

## Phase 2 (later hardening)

When data is clean and product accepts constraints:

1. Backfill `email` / `password_hash` for any legacy rows if you require `NOT NULL` everywhere (often Telegram-only rows keep `NULL` web fields).
2. Add **partial unique index** on `email` where not null, or global `UNIQUE(email)` if policy is one account per email only.
3. Optional: `NOT NULL` on `password_hash` for rows where `email` is set.

Ship as a **separate Alembic revision** after validation on staging.

## dev/stage validation checklist

- [ ] Unit: `poetry run pytest tests/unit/web/ -m unit`
- [ ] Integration (Docker Desktop running; test Postgres from `tests/docker-compose.test.yml`): `poetry run pytest tests/integration/web/ -m integration`
- [ ] Manual Telegram smoke (webhook/polling) unaffected

## Production rollout checklist

- [ ] DB migration applied and verified (`alembic current` == head)
- [ ] App deployed
- [ ] `/register` happy path + duplicate email
- [ ] Error logs clean for 30–60 minutes post-deploy
