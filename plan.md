# European Executive Job Alert Agent Implementation Plan

## Goal and planning basis

Build a working single-user application to discover, rank, review, and receive alerts about relevant European executive vacancies. Deliver a credential-free demo first, then real supported sources, persistent scheduling, and configurable email delivery.

This plan combines [the PRD](prd.md), [the informal requirements](informal_requirements.txt), and the privately supplied résumé. The PRD defines MVP behavior and acceptance criteria; the informal list supplies initial role and company priorities; the CV supplies candidate evidence, subject to review and approval. This is a plan only; implementation and live source verification have not started.

## Initial product decisions

- Start with the Netherlands, Germany, UK, Switzerland, France, and Belgium as preferred countries. Keep the broader European country list editable. Company groupings are discovery priorities, not restrictions on where those employers may have suitable vacancies.
- Preserve user-provided relocation preferences in the private candidate profile; keep the initial search geography configurable. Do not infer work authorization or sponsorship eligibility.
- Seed every title in the informal requirements as an editable alias. Group them into R&D leadership, innovation leadership, product development/formulation, technology leadership, digital R&D/transformation, and open innovation/partnerships. Evaluate executive responsibilities rather than exact title matches.
- Use the PRD defaults: hourly scans, Europe/Berlin display timezone, UTC storage, high-match threshold 80, review threshold 65, 08:00 daily digest, and configurable USD 10 monthly model budget.
- Run locally through Docker Compose. Keep notifications and external model calls disabled until configured and explicitly enabled. Document always-on hosting without deploying it.
- Use `.eml` uploads for initial LinkedIn alert ingestion. Defer mailbox integrations, inbound email hosting, additional notification channels, OCR, and bespoke ATS adapters unless separately scoped.

## Candidate evidence and matching priorities

Extract the real CV locally into a draft profile; require approval before using it for matching. Preserve excerpts and document provenance for each fact. Keep the CV and contact details out of committed fixtures, logs, and model requests.

Capture education, career dates, leadership scope, functional and sector experience, achievements, languages and mobility only from the uploaded document or explicit user corrections. Preserve supporting excerpts in the private database, not repository files. Distinguish direct reports from matrix leadership, avoid double-counting overlapping achievements and flag inconsistent titles for review.

Do not infer qualifications, language proficiency, eligibility or sponsorship. Assess adjacent sectors against approved evidence. Digital R&D roles remain eligible when responsibilities concern scientific R&D rather than unrelated software engineering.

## Priority company onboarding

Keep the informal country groupings and deduplicate employers appearing in multiple groups. Normalize spelling as proposed below, preserving original input aliases until official identities are verified.

| Priority group | Employers |
| --- | --- |
| Netherlands | JDE Peet’s, Kraft Heinz, DSM-Firmenich, AkzoNobel, IFF, Danone, Cargill |
| Germany | Henkel, Beiersdorf, BASF, Evonik, Bayer, Symrise |
| UK | Reckitt, P&G, Croda, GSK, SC Johnson, Kimberly-Clark |
| Switzerland and France | Givaudan, Nestlé, Clariant, L’Oréal, Danone |
| Belgium | Cargill, Solvay, Barry Callebaut |

Audit these 25 distinct employers first. Keep the PRD's additional starter employers in a secondary checklist. For each employer, record the verified official careers URL, ATS/board identifier, geographic coverage, access review, pagination, timestamp capabilities, and connection-test result.

Supported status requires an implemented connector and successful validation. Unsupported companies stay visible with manual/import alternatives. Greenhouse and Lever support alone does not establish coverage of this employer list. Report coverage gaps before MVP handoff; individually estimate any required Workday, SuccessFactors, or other bespoke adapter after the audit.

## Architecture and repository layout

Use FastAPI, SQLAlchemy/Alembic, PostgreSQL, React with TypeScript, and a separate Python worker sharing backend services. Use PostgreSQL for leases, scheduling state, budget reservations, and the transactional outbox; no Redis dependency is planned.

```text
backend/
  app/
    api/                 # Versioned endpoints and request validation
    models/              # Database entities
    services/            # Profiles, normalization, lifecycle, retention
    connectors/          # Greenhouse, Lever, configured HTML, imports
    matching/            # Screening, scores, evidence, provider interface
    notifications/       # Outbox, templates, SMTP and demo adapters
    worker/              # Due scans, leases, digest and delivery jobs
  migrations/
frontend/src/            # Jobs, Profile, Sources, Activity, Settings
tests/                   # Unit, PostgreSQL integration, acceptance, UI
fixtures/                # Synthetic profiles/jobs and recorded responses
docs/                    # Source matrix, onboarding, operations, API guide
```

Persist profile versions, sources, scan runs, canonical jobs, source observations, immutable job-content versions, match results, imported messages, candidate statuses/feedback, notification events, and delivery attempts. Use database constraints for observation identity and notification idempotency. Keep discovery time immutable and publication/update/receipt timestamps separate, with precision and provenance.

Expose `/api/v1` endpoints for profile upload/edit/approval, source configuration/test/scan, job filtering/details/status/merge, imports, activity, notification preview, and settings; include health and readiness endpoints.

## Implementation milestones

### 1. Foundation and runnable demo

1. Scaffold backend, frontend, migrations, Dockerfiles, Compose, environment configuration, and dependency lockfiles. Choose supported dependency versions after checking official documentation during implementation.
2. Establish formatting, linting, type checks, pytest, frontend tests, and browser acceptance tests. Add an acceptance checklist mapped to all 18 PRD criteria.
3. Build initial schema, `/api/v1` contracts, health checks, five-screen navigation, and explicit empty/error/demo states.
4. Implement local PDF/DOCX/TXT extraction, 10 MB and MIME checks, editable evidence, profile approval, and versioning. Reject unsafe uploads and handle textless PDFs with a pasted-text alternative.
5. Add synthetic demo data, including at least 20 labeled vacancies, and a local notification preview adapter. Keep supplied private documents excluded from future commits.
6. Audit priority company sources and publish the initial capability matrix before committing to live coverage.

**Exit gate:** Fresh Compose startup applies migrations and loads a labeled demo; a synthetic profile can be corrected and approved; source capabilities and unsupported employers are visible. The demo requires no API keys or outbound notifications.

### 2. Discovery, normalization, and freshness

1. Implement a typed connector contract returning jobs, completeness, warnings, and statistics. Add Greenhouse, Lever global/EU, and explicitly configured HTML parsing using JSON-LD or selectors.
2. Add manual structured imports and `.eml` parsing, retaining sender/message identity and timestamp evidence without fetching LinkedIn links. Partial descriptions remain provisional.
3. Centralize guarded HTTP fetching: validate destinations and redirects, bound response size/time/concurrency, handle pagination, honor Retry-After, and back off on transient failures.
4. Implement source testing, persisted manual scan runs, normalization, content hashes, and safe description rendering. Distinguish valid empty boards from extraction failures.
5. Deduplicate by source/external ID, then authoritative employer/requisition or application URL. Preserve identifying URL parameters; flag ambiguous similarity matches for manual merge.
6. Implement initial baseline suppression and independent published/discovered filters. Store timestamp uncertainty intervals; strict recent-publication filters require the entire interval within the requested window.

**Exit gate:** Recorded fixtures exercise all connector/import routes, pagination, changed selectors, unsafe links, duplicate imports, and timestamp edge cases. Optional live smoke tests are recorded separately with actual results.

### 3. Matching and review dashboard

1. Implement configurable hard filters and deterministic scoring: executive scope 25, function 25, sector 20, experience/capability 20, geography/preferences 10. Unknown requirements produce flags, not invented evidence or rejection.
2. Require job/profile evidence references for fit claims. Display gaps, evidence coverage, scoring method, and provisional status; scores are rankings, not hiring probabilities.
3. Add an optional model provider interface with validated output, evidence-reference checks, bounded tokens, timeout/failure fallback, and explicit external-data consent. Verify provider APIs and prices when implementing.
4. Cache by job-content version/hash, approved profile version, scoring configuration, model, and prompt version. Reserve conservative model costs transactionally before concurrent calls; stop before the monthly ceiling and continue deterministic matching.
5. Complete Jobs filters/details, profile review, source health, activity/cost views, and settings. Support all PRD candidate statuses separately from vacancy availability; collect feedback without silently changing scoring.

**Exit gate:** A formulation director outranks junior chemist and unrelated software director examples. Report precision@10 on the synthetic set, targeting at least 8 relevant results, and explain disagreements. Profile changes preserve prior results without creating new discovery alerts.

### 4. Persistent automation and notifications

1. Run due-source scans in an independent worker using renewable database leases and safe expiry/recovery. Manual and automatic scans share the same locking path; restart resumes due work without replaying every missed interval.
2. Default to two concurrent sources, one request per host, and at most three transient retries. Isolate source failures; mark capped/interrupted scans incomplete and sources stale after two missed expected intervals.
3. Reconcile closures only from definitive signals or three consecutive successful complete authoritative-source absences. Reopening preserves identity and does not automatically re-alert; email-only availability stays unverified.
4. Write eligible notification events transactionally with job/match processing. Use stable profile/job/event/channel identity across profile versions, rescans, merges, and restarts; keep digest membership separately deduplicated.
5. Batch high matches per scan, queue during quiet hours, and send one daily digest per local date across DST. Exclude provisional descriptions from immediate alerts regardless of score.
6. Implement SMTP, configured-recipient-only tests, delivery attempt records, safe retries, and explicit ambiguous-delivery status. Show preview, queued, delivered, failed, and unknown outcomes accurately.

**Exit gate:** The demo demonstrates approval → baseline scan → subsequent new vacancy → explained match → one preview notification → saved job. PostgreSQL integration tests prove worker contention, crash recovery, lifecycle rules, outbox idempotency, and digest timing.

### 5. Verification and handoff

1. Run all acceptance checks below, lint/type checks, migrations on a clean database, upgrade checks, and browser tests from documented setup steps.
2. Exercise 30 configured sources and 5,000 stored jobs with controlled fixtures. Measure scan duration, dashboard responsiveness, and notification enqueue delay against PRD targets; report constrained sources separately.
3. Test export, profile/cache deletion, configurable retention, backup/restore, and worker restart. Default to deleting raw résumé uploads after approval and retaining raw emails/logs for 30 days; document backup expiry separately.
4. Deliver README, exact commands, `.env.example`, API reference, source onboarding guide, capability matrix, test results, demo walkthrough, and honest limitations.
5. Document authentication, HTTPS, secure sessions/CSRF where relevant, and always-on hosting requirements before any internet deployment. Keep local binding on localhost.

**Exit gate:** All offline acceptance checks pass; any unexecuted credential-dependent/live checks are explicitly listed. The final matrix names which requested employers are actually monitored and which need manual import or future adapters.

## Acceptance coverage

| PRD criteria | Required verification |
| --- | --- |
| 1 | Upload validation, extraction, correction, approval |
| 2–3 | Ranking quality; unknown language/sponsorship preserved |
| 4–5 | Connector normalization, pagination, malformed response and selector failures |
| 6–7 | Publication uncertainty, discovery filters, UTC/DST, update-time separation |
| 8–10 | Baseline suppression, restart/retry idempotency, distinct requisitions and cross-source merge |
| 11–12 | Closure/reopening rules; `.eml` ingestion with zero LinkedIn requests |
| 13–14 | 429 handling, isolated failures, concurrent worker leases, safe delivery retries |
| 15–16 | No-key demo, budget exhaustion, profile/cache versions without old alerts |
| 17 | Prompt injection, SSRF/redirect/DNS checks, XSS, unsafe uploads |
| 18 | Fresh Compose setup, migrations, seed, dashboard, scheduled worker, mock delivery |

Use recorded fixtures for repeatability and real PostgreSQL for transaction/lease tests. Use a fake clock for freshness, quiet hours, and DST. Mock SMTP/provider failures and assert network boundaries. Keep live connector/provider/email checks opt-in and separate from the default suite.

## Planned developer commands

These commands are targets to implement and document; they do not exist yet.

| Command | Purpose |
| --- | --- |
| `docker compose up --build` | Start web/API, worker, database, migrations, and configured demo |
| `docker compose run --rm web python -m app.demo seed` | Idempotently seed synthetic data in demo mode |
| `docker compose run --rm web alembic upgrade head` | Apply database migrations explicitly |
| `docker compose run --rm web pytest` | Run backend tests with the configured test database |
| `npm --prefix frontend run dev` | Start frontend development server |
| `npm --prefix frontend run build` | Produce frontend production assets |
| `npm --prefix frontend run check` | Run frontend lint and TypeScript checks |
| `npm --prefix frontend test` | Run frontend unit tests |

## Decisions deferred until setup

There are no blocking product questions for local implementation. Before enabling live operation, confirm recipient/SMTP settings, any hard sponsorship or relocation constraints, desired source coverage beyond the supported MVP, and whether to enable a paid matching provider. These settings remain editable; absent answers do not block the credential-free demo. Any expansion to Dubai/Singapore, bespoke ATS integrations, or public hosting should be scoped explicitly.
