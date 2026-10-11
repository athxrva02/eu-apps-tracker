# Validation — 11 October 2026

## Executed checks

| Check | Result |
|---|---|
| Backend acceptance suite, `pytest -q` | **65 passed** on SQLite; one upstream Starlette TestClient/httpx deprecation warning |
| Ruff lint and formatting | Passed |
| Frontend TypeScript and Prettier | Passed |
| Frontend Vitest | **4 passed** |
| Production Vite build | Passed; approximately 281 kB JavaScript / 86 kB gzip |
| Alembic schema comparison | No pending migration operations |
| Fresh SQLite migration lifecycle | Upgrade → schema check → downgrade → upgrade passed on isolated database |
| API + worker demo | 24 baseline jobs, second scan discovered job 25, durable discovery preview, worker heartbeat; no SMTP mail or model calls |
| Synthetic ranking | **Precision@10: 10/10**, above the 8/10 fixture gate; not evidence of real-world accuracy |
| 5,000-job API case | Returns all records with bounded SQL queries; UI renders 30 cards at a time |
| SQLite online backup | Backup integrity passed, 25 demo jobs recovered |
| Compose configuration | `docker compose config --quiet` passed |
| Requested OpenRouter smoke check | **One live POST**, HTTP 200, valid structured `{"status":"OK"}`, `openai/gpt-4o`, 125 tokens, **$0.00035**; no candidate data |
| Credential checks | Supplied key absent from source and frontend bundle; ignored `.env` has mode 600 |

Frontend checks ran on installed Node 23.9.0. Vitest warns this odd-numbered version is outside its supported engine range, though tests passed. Use **Node 24 LTS**, as specified in the Dockerfile. Backend tests never make paid requests. Full OpenRouter matching, evidence redaction and cost accounting are separately tested with a mocked transport.

## PRD acceptance mapping

| Criteria | Automated evidence |
|---|---|
| 1 — résumé lifecycle | MIME/archive validation, safe DOCX extraction, contact redaction, corrections, version-preserving approval |
| 2–3 — ranking and unknowns | 24 labeled synthetic vacancies, junior/software exclusions, provisional evidence, unknown sponsorship retained |
| 4–5 — connectors | Greenhouse update/publication separation, Lever EU pagination and loop detection, JSON-LD, CSS selector validation and changed-page errors |
| 6–7 — timestamps | Strict intervals, future exclusion, date-only uncertainty, UTC boundaries, DST 23-hour day and quiet hours |
| 8–9 — alert idempotency | Baseline suppression, repeat ingestion, durable matching crash recovery, unique discovery identity and batch gating |
| 10 — deduplication | Email/employer canonical URL merge, distinct requisitions including shared generic URL, manual merge preserves delivery evidence |
| 11 — closures | Failed/incomplete scans preserve jobs; three complete absences; second authoritative source; reopen identity |
| 12 — `.eml` | LinkedIn fixture imported with network disabled, bounded Message-ID hash, receipt distinct from publication |
| 13 — scheduling | Retry-After honored, private DNS/redirect rejection, atomic lease contention/expiry, worker isolates failed sources |
| 14 — notifications | Definite failure retries, ambiguous delivery not retried, demo never calls SMTP, scan batch grouping |
| 15 — budget | No-key fallback, exhausted budget makes no calls, concurrent reservations, missing usage retains conservative reservation |
| 16 — profile changes | Approved version preserved, new match caches, no old discovery alerts resent |
| 17 — untrusted inputs | HTML sanitation, SSRF/ZIP protection, unsupported model evidence rejected, no model tools |
| 18 — deployment | Migration/API/worker/demo components pass; Compose syntax passes. **Full Docker/PostgreSQL startup and browser interaction remain unverified.** |

## Blocked or unexecuted checks

- **Docker/PostgreSQL:** Docker CLI reports its daemon is not running. No successful container build/start or PostgreSQL integration test is claimed.
- **Browser/visual QA:** Chrome exits with SIGABRT when Playwright launches it in this sandbox. No visual pass or screenshots are claimed. Run this optional test on a local demo server after building and starting the app:

  ```sh
  .venv/bin/playwright install chromium
  .venv/bin/python scripts/check_ui.py --url http://127.0.0.1:8000
  ```

  It checks five screens, job details, browser errors and mobile overflow; screenshots go to ignored `test-results/`.
- **Live career sources:** Implemented connector families are fixture-tested. All 25 target employers remain unsupported/disabled until individually configured, reviewed and tested. Official entry-page discovery is not a connector smoke test.
- **Live SMTP:** Not configured or sent. Delivery behavior uses a fake sender and demo previews.
- **Real-world ranking:** Synthetic descriptions exercise concept overlap. Adjacent jobs, multilingual descriptions, synonyms and executive scope require human review.

## Practical limits

No LinkedIn browsing, application submission, recruiter messaging, OCR, authenticated ATS scraping or career-page JavaScript rendering. Role aliases record search intent; connectors retrieve full configured boards. Conditional HTTP caches are session-local. Scheduling requires an awake machine or always-on host. SMTP ambiguity stays visible without blind resends. Separate backups have their own retention policy. See [sources](sources.md) and [operations](operations.md) for setup details.
