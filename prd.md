European Executive Job Alert Agent
Product requirements document • Version 1.0 • 11 October 2026
1. Build instruction
Build a working, single-user application that monitors a configurable list of European company career sites, imports job alerts, matches vacancies against an approved résumé and target profile, and sends concise notifications for newly discovered relevant jobs. Deliver runnable code, migrations, automated tests, Docker configuration, sample fixtures, and setup documentation. This document defines the MVP and acceptance criteria. Implement the MVP before optional features.
Do not stop at a prototype UI. The application must fetch real supported sources, persist results, run scheduled scans, explain matches, and deliver notifications when credentials are configured. It must also run end to end in demo mode without paid services or credentials. Never present fixtures as live results.
2. User and problem
The primary user is an executive with approximately 25 years of experience, currently Global Format Lead for Cif Sprays at Unilever, seeking director-level opportunities in Europe related to chemical engineering, R&D, innovation, and product development. His son will configure and maintain the application.
Relevant vacancies are scattered across corporate career sites, recruitment platforms, and LinkedIn. Executive titles vary widely, and keyword alerts often return junior roles or unrelated disciplines. The product should reduce manual searching while preserving enough evidence for the candidate to judge each opportunity.
Only the facts above are confirmed for the initial profile. Degrees, exact employment dates, leadership scope, achievements, languages, salary expectations, location preferences, and work authorization must come from the uploaded résumé or user input. Do not fabricate them.
3. Goals and boundaries
Goals
- Discover new vacancies from explicitly configured sources on a recurring schedule.
- Rank opportunities by executive scope, functional relevance, sector fit, and candidate evidence.
- Support views for vacancies published within the last hour or 24 hours, with honest timestamp precision.
- Also show jobs first discovered within those windows when publication time is unavailable.
- Send useful alerts with few duplicates and clear reasons for matching.
- Make source failures, unsupported sites, and coverage gaps visible.
- Keep hosting and model costs configurable and measurable.
Outside the MVP
- Applying to jobs, submitting résumés, contacting recruiters, or automating LinkedIn messages.
- Searching the entire web or guaranteeing every European executive vacancy is found.
- Inferring hidden executive search mandates or unpublished jobs.
- Automated browsing of LinkedIn, CAPTCHA bypass, rotating proxies, or use of LinkedIn session cookies.
- Multi-user SaaS, billing, mobile apps, résumé rewriting, or interview preparation.
4. Defaults and configuration
All defaults below are implementation choices, not confirmed candidate preferences.
Setting	MVP default
Search geography	Europe, including the UK and Switzerland; editable country list
Preferred countries	Unspecified until configured
Role families	R&D, innovation, formulation, product development, technology leadership
Target levels	Director, Senior Director, Head of, VP, Global or Regional Lead with executive scope
Industries	Chemicals, specialty chemicals, home care, consumer products, materials, coatings, ingredients
Adjacent opportunities	Manufacturing or process leadership only when profile evidence supports fit
Work authorization	Unknown; never assume eligibility or sponsorship
Job language	No hard exclusion by default; report stated language requirements
Scan interval	60 minutes per source; configurable to 15 minutes where permitted and practical
Display timezone	Europe/Berlin; store all instants in UTC
High-match threshold	80 out of 100
Review threshold	65 out of 100
Notifications	Email adapter, disabled until recipient and credentials are configured
Digest	Daily at 08:00 in display timezone
Initial import	Establish baseline; include in dashboard, suppress immediate alerts
Monthly LLM budget	USD 10 configurable ceiling; verify current prices during implementation


Target examples: R&D Director, Innovation Director, Director of Product Development, Head of Formulation, Global R&D Lead, Technical Director, and VP R&D. A title is a retrieval signal, not proof of suitable seniority. Evaluate responsibilities, decision-making scope, team leadership, and strategic remit.
Proposed exclusions include internships, graduate roles, laboratory technician roles, unrelated software engineering, and clearly junior individual contributor positions. Exclusions must be editable. A word such as “manager” must not automatically exclude a strategically senior role.
Provide a starter company checklist including Unilever, Reckitt, Henkel, P&G, BASF, Dow, Evonik, AkzoNobel, DSM-Firmenich, Covestro, Clariant, Croda, Solvay, Syensqo, Nouryon, and Arkema. These are proposed search targets, not verified hiring companies or supported integrations. Verify each official careers URL and connector before enabling it. An unimplemented site must display “unsupported” rather than appear monitored.
5. Main user journey
1. Upload a résumé in PDF, DOCX, or plain text, or paste résumé text.
2. Review extracted experience, skills, industries, and leadership evidence. Correct and approve the profile before matching.
3. Configure countries, target roles, exclusions, optional relocation or sponsorship requirements, thresholds, and alert destination.
4. Add career sources by URL or supported ATS identifier. Run a connection test and see the source capability report.
5. Run the initial scan to establish a baseline.
6. Review ranked jobs, inspect match evidence, save or dismiss opportunities, and open the original posting.
7. Receive alerts after subsequent scans and review the daily digest.
8. Inspect source health and adjust preferences when coverage or match quality is poor.
6. Functional requirements
FR1 Résumé and profile
Accept PDF, DOCX, and TXT up to 10 MB. Reject unsupported files and MIME mismatches. Extract locally where possible. If a PDF has no extractable text, explain the limitation and offer pasted text; OCR is optional.
Represent experience, role history, functions, sectors, skills, education, achievements, leadership evidence, languages, and preferences as editable fields. Keep provenance pointing to résumé excerpts or user-entered values. User corrections take precedence. Do not send contact details, home address, or identifiers to the matching model.
Version the approved profile. Re-scoring after a profile change must preserve old results for audit and must not resend previously delivered new-job alerts by default.
FR2 Source registry and capability reporting
Each source records company, official URL, connector type, external board identifier, enabled state, scan frequency, timezone assumptions, pagination behavior, timestamp availability, access basis, and last successful scan.
Implement a common connector interface that returns normalized jobs, pagination completeness, warnings, and scan statistics. Supported initial routes:
- Greenhouse public Job Board API.
- Lever public Postings API, including global and EU endpoint configuration.
- A configurable HTML connector for permitted public pages, using JSON-LD JobPosting where available and explicit selectors otherwise.
- Manual structured job import and imported alert emails.
Workday, SAP SuccessFactors, and other bespoke sources are later adapters unless individually implemented and tested. Do not pretend a generic parser provides universal support. Use Playwright only for supported public pages requiring JavaScript and where permitted. Do not bypass access restrictions. Record robots and terms review as source configuration; robots permission alone is not a complete access determination.
Connection testing must distinguish valid empty results, blocked access, bad identifiers, parser failures, and unsupported sources. Never interpret a failed extraction as an empty board.
FR3 LinkedIn and alert imports
Support user-uploaded or forwarded LinkedIn job-alert emails as an input channel. MVP ingestion is an .eml upload or a configured dedicated inbound email endpoint; full Gmail or Outlook access is optional and requires separate explicit setup.
Extract only jobs contained in the provided message. Retain sender, received time, message ID, job links, and timestamp evidence. Deduplicate repeated messages. Do not visit LinkedIn automatically to enrich or validate a job. Provide a manual link for the user.
A partial email description yields a provisional match labeled “limited evidence.” Never invent the missing description. If the email provides a verified external employer URL, the employer connector may enrich it under that source's rules. Otherwise enrichment is manual.
The app cannot promise one-hour LinkedIn coverage: its visibility depends on when LinkedIn sends alerts and when they are imported. Display this limitation in source status.
FR4 Scheduling and fetching
Run an independent persistent worker, not a scheduler dependent on an open browser or web request. Support automatic scans, manual scans, pause/resume, and per-source configuration. Prevent overlapping scans of the same source through database-backed leases.
Use request timeouts, bounded concurrency, pagination limits, conditional requests where supported, jitter, and exponential backoff. Honor Retry-After. Proposed defaults: two simultaneous sources, one request at a time per host, at most three transient retries. A source failure must not cancel other sources.
After downtime, resume due scans without attempting one run per missed interval. Full pagination is required to claim a complete scan. Mark interrupted or capped scans incomplete.
FR5 Freshness and lifecycle
Keep separate fields for source publication time, source update time, first observation, latest observation, and email receipt time. Store raw timestamp text, timezone interpretation, precision, and provenance.
Define two independent filters:
- Published recently: use source publication evidence only. Include a job in a strict one-hour view only when its publication time or entire uncertainty interval falls inside the window. Date-only or vague relative dates cannot establish one-hour freshness.
- Discovered recently: use immutable first_seen_at. Label this explicitly; discovery does not imply recent publication.
“Posted today,” date-only values, and “one day ago” must retain their uncertainty. Missing publication time remains unknown. Never substitute updated_at or first_seen_at as published_at.
First import creates a baseline. Subsequent genuinely new identities may trigger alerts even if publication time is unknown, labeled “newly discovered.” A changed description is an update, not a new job.
Mark a job closed only when the connector provides a definitive closed signal, or it is absent from three consecutive successful, complete scans of its authoritative source. Failures or incomplete scans never count. Imported email-only jobs remain “availability unverified” until manually resolved or enriched. A returning same-ID job is reopened and does not automatically trigger another new-job alert.
FR6 Normalization and deduplication
Normalize title, employer, locations, country codes, work mode, employment type, description, canonical URLs, and external requisition identifiers. Preserve source text and language. Escape rendered content and strip unsafe HTML.
Use source plus external job ID as the primary observation identity. Merge cross-source observations into a canonical job when an authoritative requisition ID or normalized employer application URL agrees. Otherwise compute similarity over employer, title, locations, and description; ambiguous matches remain separate and can be manually merged. Different requisitions with the same title remain separate. Preserve multiple locations and every source link.
Avoid tracking parameters when comparing URLs, but preserve parameters needed to identify the vacancy. Store content hashes to detect updates and avoid repeated model calls.
FR7 Matching and explanations
Use deterministic screening before optional LLM evaluation. Reject only explicit hard-filter violations; an unknown requirement produces an uncertainty flag, not a rejection. Examples: a confirmed job location outside the configured region, explicit junior scope, or an excluded function. Remote roles require evidence that work from the configured region is permitted.
Proposed configurable score weights, totaling 100:
Dimension	Weight	Evidence
Executive scope	25	Strategic responsibility, leadership, budget or portfolio scope
Function fit	25	R&D, formulation, innovation, technical product development
Sector fit	20	Relevant chemical, materials, consumer or home-care context
Experience and capability	20	Requirements compared with approved résumé evidence
Geography and preferences	10	Stated location, work mode, language and user preferences


Return dimension scores, total, matched evidence, gaps, unknowns, recommendation, and evidence coverage. These scores are heuristic rankings, not probabilities of receiving an offer. Do not inflate a score because a description repeats keywords. Avoid counting the same achievement repeatedly.
LLM output must follow a validated JSON schema. Every match claim points to both a job excerpt and profile evidence where applicable. Unknown languages, sponsorship, salary, or qualifications stay unknown. Never infer work authorization from nationality or location.
Immediate alerts require score >=80, sufficient description evidence, and no hard-filter violation. Jobs scoring 65–79 appear in the review queue and digest. Partial descriptions remain provisional regardless of score and are excluded from immediate alerts by default.
Provide deterministic matching when no model is configured, when the budget is exhausted, or when the model fails. Label matching method and confidence limitations. Cache by normalized job content hash, profile version, scoring configuration, model, and prompt version.
FR8 Notifications
Implement email using a configurable SMTP adapter. Optional later channels: Telegram, Slack, or push notifications. No notifications are sent until the user configures a destination and enables sending. A preview/test action sends only to that configured destination.
Each alert contains title, company, locations, score, three concise fit reasons, important gaps, freshness label, source, and the original application link. Do not include the résumé attachment or full résumé text.
Batch high matches discovered in a scan into one message. Daily digest includes newly discovered high/review matches not previously included in that digest, pending provisional matches in a separate section, and source failures. Quiet hours are configurable; queue immediate alerts until quiet hours end. Digest scheduling must handle daylight-saving changes and send once per local day.
Use a transactional notification outbox and delivery ledger keyed by profile, canonical job, event type, and channel. Persist provider IDs and retries. Repeated scans must not create duplicate messages. Where delivery acknowledgement is ambiguous, mark delivery unknown and avoid blind resend; do not claim universal exactly-once delivery.
FR9 Dashboard
Provide five screens: Jobs, Profile, Sources, Activity, and Settings.
Jobs supports freshness basis, 1-hour/24-hour/7-day windows, match score, country, company, function, source, work mode, and candidate status. Default order: score descending, then first observation descending. Statuses: new, saved, dismissed, applied, interview, offer, archived. Candidate status is separate from vacancy availability.
Job details show original and normalized description, source links, timestamp precision, matching method, evidence, gaps, and scan history. Provide user feedback such as “too junior,” “wrong sector,” and “good match.” Store feedback; do not silently modify thresholds or train a model in the MVP.
Activity displays scans, result counts, completeness, errors, next run, model usage, costs, and notification outcomes. Sources show last success and stale status after two missed expected intervals. Empty UI states explain whether there are no matches, no sources, or failed scans.
7. Architecture and data
Recommended implementation: Python FastAPI backend; SQLAlchemy and Alembic; PostgreSQL; React with TypeScript frontend; separate Python worker sharing the backend services; Docker Compose for web, worker, and database. Use currently supported stable dependencies and pin versions during implementation. Redis is unnecessary for the MVP unless a demonstrated requirement emerges.
Use a provider interface for optional LLM matching. The model name, key, token limits, budget, and estimated token prices must be configurable. Verify API details against current official documentation during implementation. ChatGPT Plus and API usage have separate billing; the deployed application must not assume a Plus subscription supplies API credits or use ChatGPT browser automation as its backend.
Core entities:
- CandidateProfile and ProfileVersion: approved evidence and preferences.
- Source: configuration, capabilities, access status, schedule and health.
- ScanRun: source, start/end, completeness, counts, error, lease state.
- CanonicalJob: normalized vacancy and availability.
- JobObservation: source ID, canonical job ID, raw fields, timestamp evidence, first/last seen and content hash.
- MatchResult: profile version, job content version, scoring/prompt/model versions, scores, evidence, gaps, costs.
- ImportedMessage: external message ID/hash, received time and import outcome.
- CandidateJobStatus and Feedback: user decisions.
- NotificationOutbox and DeliveryAttempt: idempotency key, payload, provider result and retries.
Use migrations, unique constraints, transactions, UTC-aware timestamps, and database-backed worker leases. Expose versioned endpoints for profile upload/approval, source CRUD/test/scan, jobs/detail/status, message imports, runs, notification preview, and settings. Implement health and readiness endpoints.
8. Security and privacy
Local deployment binds to localhost by default. Internet deployment requires authentication and HTTPS, with secure session cookies and CSRF protection where appropriate. Do not expose an unauthenticated administration UI.
Keep API keys and SMTP secrets in environment variables or a secret store, never frontend bundles, repository files, or logs. Redact sensitive input from logging. Résumé and job text are untrusted data; embedded instructions must not change the model's task or invoke tools. Matching models receive no browser, shell, email, or application-submission capabilities.
Prevent SSRF from submitted source URLs, redirects, application URLs, and imported email links: allow HTTP(S) only, block private/loopback/link-local destinations, check DNS and redirects, and use explicit connector host allowlists where possible. Prevent uploaded file path traversal and archive expansion abuse. Sanitize descriptions and email HTML to prevent XSS.
Explain before enabling external model calls that selected résumé evidence and job descriptions will be sent to the configured provider. Support deleting résumé uploads and profile data, exporting results, and backing up the database. Default raw-upload retention: delete after profile approval unless the user opts to retain it. Raw imported email retention: 30 days. Logs: 30 days. Make retention configurable and apply deletion to associated caches; document backup expiration separately.
9. Operational requirements
- Starter capacity target: 30 configured sources and 5,000 stored jobs on a small single-host deployment.
- Healthy supported sources should complete a typical scan within 10 minutes under default concurrency; document slower or constrained sources.
- For enabled immediate alerts, enqueue within 5 minutes after matching completes, outside quiet hours and excluding provider outages.
- Polling provides detection on the next successful scan, not a guarantee of notification within one hour of publication.
- Track requests, fetch duration, failures, parse completeness, model calls/tokens, estimated spend, matches, and delivery results.
- Stop model calls before the configured budget ceiling using conservative preflight estimates. Continue fetching and deterministic matching. Display budget exhaustion clearly.
- No single-source outage may prevent other scans or the dashboard from functioning.
- Provide restart, backup/restore, scheduler deployment, and credential setup instructions. A laptop must remain awake and connected for local scheduling; document an always-on host option without deploying it automatically.
10. Acceptance criteria
Use recorded fixtures for repeatable tests and a documented optional live smoke test. Required test cases:
1. A résumé can be uploaded, parsed, corrected, and approved; unsupported and oversized files are rejected.
2. A relevant director-level formulation vacancy ranks above a junior chemist and an unrelated software director vacancy in labeled fixtures.
3. Unknown sponsorship or language never becomes an invented match claim or automatic hard rejection.
4. Greenhouse and Lever connectors normalize valid fixtures, retrieve all pages where applicable, and report malformed responses as failures.
5. A configured HTML connector parses a documented public-page fixture; changed selectors surface an error rather than a successful zero-job scan.
6. A date-only posting is excluded from strict one-hour freshness; it remains available in discovered-recently views with the correct label.
7. Source updated_at is never displayed as publication time. UTC boundaries and daylight-saving transitions pass tests.
8. Initial import generates no immediate new-job alerts. A new job on the next scan triggers one eligible alert.
9. Repeated scans, imported copies, model retries, and process restarts do not create duplicate new-job outbox events.
10. Two genuinely different requisitions with identical titles remain separate; a LinkedIn email copy and matching employer URL merge correctly.
11. Failed or incomplete scans never close jobs. Three complete absences close an authoritative-source job, and reopening preserves its identity.
12. A LinkedIn .eml fixture imports without any request to LinkedIn; partial descriptions remain provisional.
13. A 429 honors backoff; one failed source does not stop others; duplicate workers cannot scan the same source concurrently.
14. Notification provider failure retries safely. Ambiguous delivery is visible and does not trigger uncontrolled resends.
15. No API key produces a functional deterministic demo. Budget exhaustion stops model calls while scans continue.
16. Profile changes invalidate relevant match caches without resending old discovery alerts.
17. Malicious résumé/job instructions cannot change matching behavior or cause tool calls; unsafe URLs and script content are blocked.
18. Docker Compose starts successfully from documented steps; migrations, demo seed, dashboard, scheduled worker, and mock notification flow work end to end.
For ranking evaluation, supply a clearly synthetic labeled set of at least 20 vacancies spanning strong matches, adjacent roles, misleading senior titles, junior roles, unknown requirements, and multilingual titles. Report precision among the top 10 and explain disagreements. Treat an initial target of at least 8 relevant top-10 results as a fixture quality gate, not proof of real-world matching accuracy.
11. Delivery sequence
Milestone 1 Foundation
Create repository structure, configuration, database migrations, profile approval, source registry, fixtures, and runnable demo. Implement security boundaries early.
Milestone 2 Discovery
Implement Greenhouse, Lever, configurable HTML, manual imports, and .eml imports. Add scans, normalization, freshness, deduplication, baseline handling, and source health.
Milestone 3 Matching and review
Implement deterministic scoring, optional schema-validated LLM matching, evidence display, profile versioning, budget limits, dashboard filtering, and candidate statuses.
Milestone 4 Automation
Implement persistent scheduler, worker leases, lifecycle reconciliation, outbox, SMTP alerts, digest, quiet hours, and delivery diagnostics.
Milestone 5 Verification and handoff
Run acceptance tests, lint/type checks, migration checks, and end-to-end demo. Deliver a support matrix documenting implemented versus unsupported sources. List remaining limitations and exact setup needed for live sources and alerts. Do not mark credential-dependent smoke tests passed unless actually executed.
12. Required deliverables
- Working source code with dependency lockfiles and database migrations.
- README with local setup, production authentication requirements, always-on scheduling, source setup, costs, backups, and troubleshooting.
- Docker Compose and .env.example containing placeholders only.
- Sample approved profile, synthetic vacancies, recorded connector fixtures, and demo-mode notification preview.
- Automated acceptance tests and their results.
- Connector capability matrix, API reference, and source onboarding guide.
- Short demonstration of résumé approval → baseline scan → new vacancy → explained match → notification → saved job.
13. References and implementation constraints
Checked on 11 October 2026. Recheck current documentation during implementation; these links establish constraints, not guaranteed endpoint stability.
- OpenAI billing: https://help.openai.com/en/articles/9039756-managing-billing-settings-on-chatgpt-web-and-platform — API usage is billed separately from a ChatGPT subscription.
- LinkedIn prohibited software: https://www.linkedin.com/help/linkedin/answer/a1341387/prohibition-of-scraping-software?lang=en — LinkedIn prohibits third-party scraping and automated website activity. Implement email/manual ingestion; do not promise unrestricted access through a public jobs API.
- Greenhouse Job Board API: https://docs.greenhouse.io/job-board.html — public job-board retrieval documentation. Do not treat job update fields as publication timestamps.
- Lever Postings API: https://github.com/lever/postings-api — public posting retrieval, with global and EU configurations. Preserve the actual timestamp capabilities of returned data.
14. Prompt to give Codex with this document
Build the MVP defined in this PRD in the current repository. First inspect the repository and applicable instructions, then implement in the milestone order. Make routine implementation decisions independently and document assumptions. Ask only for information that blocks useful progress. Start with fixtures and demo mode so the app works without credentials. Implement real supported connectors rather than simulated integrations. Preserve timestamp uncertainty, explain résumé matches, and make unsupported sources visible. Do not automate LinkedIn browsing or submit applications. Run the acceptance tests and deliver working code, setup instructions, test results, and an honest limitations list. This request authorizes local implementation; external deployment and real notification sending require separately configured credentials and explicit enablement.