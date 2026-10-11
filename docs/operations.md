# Operations and data handling

## Scheduling and restart

Compose runs a separate worker with `restart: unless-stopped`. Its ten-second loop scans due enabled sources, reconciles durable matching work, schedules the local-date digest and delivers due outbox events. Source and host leases use atomic database operations; renewal protects long scans and expired leases permit recovery. Matching work is committed with ingestion, so restarts resume pending jobs and use unique outbox identities to prevent duplicate discoveries. Profile/settings changes also leave a durable rescore marker.

The local worker must remain running, awake and connected. For continuous service, deploy the same Compose stack on a maintained always-on host with persistent PostgreSQL storage, encrypted disks, automatic OS updates and backup monitoring. Deployment is not automated by this repository. Bind the web service to localhost behind an authenticated HTTPS reverse proxy; set a long random `ADMIN_TOKEN`. Keep development tooling private. Browser tokens are stored in session storage, not cookies; write requests reject foreign origins.

Use `docker compose logs --tail=100 worker web` to inspect operational errors. Activity shows scan completeness, warnings, failed sources, notification attempts and model costs. An active worker updates its heartbeat every 15 seconds. Sources become stale after two expected scan intervals without success. A failed connection test does not mean there are zero jobs.

## Back up and restore

Backups contain candidate evidence, job records and delivery history. Restrict permissions and encrypt backups. Retain only as long as necessary; a suggested operational policy is seven daily backups. Application deletion cannot erase separately retained backups.

PostgreSQL backup, from the repository root:

```sh
mkdir -p private_inputs/backups
umask 077
docker compose exec -T db pg_dump -U jobagent -d jobagent -Fc > private_inputs/backups/jobagent.dump
```

To restore, stop writes, create a **new empty** database using a separate Compose project/volume, then restore its dump. Do not use `--clean` against an existing database unless its replacement is intentional.

```sh
docker compose stop web worker
docker compose exec -T db createdb -U jobagent jobagent_restored
docker compose exec -T db pg_restore -U jobagent -d jobagent_restored < private_inputs/backups/jobagent.dump
```

For Compose, set `POSTGRES_DB=jobagent_restored` in `.env` and run `docker compose up -d` to recreate init/web/worker with the restored database. For local services, point `DATABASE_URL` at the restored database, apply `alembic upgrade head`, and restart web/worker. Source leases expire naturally; previously `sending` mail becomes `unknown` and must be investigated before a manual resend. Never automatically resend ambiguous SMTP deliveries. Test restores on isolated databases.

SQLite development backup uses its online backup API, including WAL changes:

```sh
.venv/bin/python scripts/backup_sqlite.py .data/agent.sqlite private_inputs/backups/local.sqlite
```

Stop web/worker before restoring SQLite. Copy the backup to a new path, point `DATABASE_URL` there, and migrate before starting. Do not copy a live `.sqlite` file alone while WAL writes are occurring.

## Privacy, retention and costs

Résumé uploads and raw `.eml` bytes are processed in memory and never stored. DOCX is size/expansion checked; PDF parsing does not enable OCR. Profile excerpts remain editable and versioned. Uploaded documents and job text cannot provide tool instructions. Missing candidate facts stay unknown. Keep personal names/addresses out of curated model evidence; common email/phone/LinkedIn contact patterns are redacted but redaction is not exhaustive.

The worker deletes imported-email metadata and ended scan logs after their configurable retention periods (30 days by default). Pending matching runs are retained until processed. Job observations, versions, matching history, usage and notification delivery records persist for deduplication/audit. Delete Profile Data removes profile versions, matching caches, imported-email metadata and notification records; it does not delete jobs or separately retained backups. Export includes approved profile evidence and discovered job/source data, so store it privately.

OpenRouter calls require configured server-side credentials, current per-token pricing, consent and explicit enablement. A strict schema requires valid cited excerpts/evidence IDs. Hard filters and provisional flags remain deterministic. In-flight and uncertain usage count against the monthly budget; charges reported by OpenRouter reconcile reservations. Budget exhaustion leaves discovery and deterministic ranking working. A reservation is a conservative estimate, not an upstream billing guarantee. Model changes require restarting web/worker and triggering a rescore through Settings/profile approval.

SMTP is disabled until credentials, recipient and notifications are configured. Demo mode always previews mail, even if SMTP credentials exist. Failed-before-acceptance deliveries retry at two and four minutes; the third failure stops. Ambiguous acceptance is never retried. The digest is unique per configured local date, including DST; scheduler downtime produces the current day's digest when the worker returns rather than replaying every missed date.

## Troubleshooting

- **Empty dashboard:** migrate, approve a profile, configure/import sources, and inspect Activity. Seeding requires `DEMO_MODE=true` and synthetic data must stay separate from live data.
- **Source unsupported or incomplete:** check board/region, allowed hosts, pagination, access review and changed selectors. Do not bypass login or CAPTCHA.
- **No new-job email:** baseline jobs are suppressed; scores below threshold, limited descriptions, quiet hours or disabled notifications explain most cases.
- **Model stays deterministic:** confirm key, model schema support, data-policy routing, token prices, consent and budget. Provider failures are reported without exposing credentials.
- **Database unavailable:** verify Compose database health and environment URL. SQLite is a local convenience; validate PostgreSQL on the deployment host.
