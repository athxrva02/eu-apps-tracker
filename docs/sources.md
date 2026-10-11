# Sources and coverage

## Supported connector families

| Family | Configuration | Completeness and publication |
|---|---|---|
| Greenhouse public Job Board API | `board`, `access_reviewed`, review notes | Full job-list response; compare supplied total. `updated_at` remains update evidence. Publication is unknown unless explicitly supplied as `first_published`. |
| Lever public Postings API | `board`, `region: global/eu`, optional page size/cap | Paginate `skip`/`limit` until a short page; repeated IDs fail; caps remain incomplete. Public API publication remains unknown. |
| Configured public HTML | Exact URL, allowed redirect hosts, single-page declaration or next selector; timezone | Parse JSON-LD JobPosting, otherwise configured row selectors. Missing jobs without an explicit empty marker fail. Incomplete pagination cannot close jobs. |
| Structured manual import | JSON array in Import jobs | User-supplied evidence; no source fetching. First complete import establishes a baseline. |
| Uploaded `.eml` alert | Import jobs → email | Parse provided links and local import time; Message-ID/hash dedup. No tracking redirects or LinkedIn requests. Descriptions remain provisional. |

These are implemented adapter families, **not verified integrations with the companies below**. Adapter tests use fixed synthetic response shapes. Real Greenhouse/Lever/company fetch smoke tests were not run. Public API documentation: [Greenhouse](https://developers.greenhouse.io/job-board.html), [Lever](https://github.com/lever/postings-api). HTML does not execute JavaScript, resolve CAPTCHA, or log into an ATS.

## Employer entry-page checklist

Official entry pages were identified on 11 October 2026. Every employer below is seeded as **unsupported, disabled**. For every row, ATS identifier, permitted access, pagination, country completeness and timestamp precision remain unvalidated. Priority countries reflect the informal requirements, not confirmed vacancy coverage. Follow the linked official pages manually to review access and identify a supported endpoint.

| Employer | Priority countries | Official entry |
|---|---|---|
| JDE Peets | NL | [Careers](https://www.jdepeets.com/careers/exploreopportunities/) |
| Kraft Heinz | NL | [Careers](https://careers.kraftheinzcompany.com/) |
| DSM-Firmenich | NL | [Careers](https://careers.dsm-firmenich.com/en/careers.html) |
| AkzoNobel | NL | [Careers](https://careers.akzonobel.com/) |
| IFF | NL | [Careers](https://www.iff.com/careers/) |
| Danone | NL, FR | [Careers](https://careers.danone.com/en-global/jobs.html) |
| Cargill | NL, BE | [Careers](https://careers.cargill.com/en/search-jobs) |
| Henkel | DE | [Careers](https://www.henkel.com/careers/find-your-job-apply) |
| Beiersdorf | DE | [Careers](https://www.beiersdorf.com/career/your-application/job-search) |
| BASF | DE | [Careers](https://www.basf.com/global/en/careers) |
| Evonik | DE | [Careers](https://www.evonik.com/en/careers/jobs.html) |
| Bayer | DE | [Careers](https://www.bayer.com/en/careers) |
| Symrise | DE | [Careers](https://www.symrise.com/your-career/search-and-apply/) |
| Reckitt | GB | [Careers](https://careers.reckitt.com/) |
| P&G | GB | [Careers](https://www.pgcareers.com/global/en) |
| Croda | GB | [Careers](https://www.croda.com/en-gb/careers/current-vacancies) |
| GSK | GB | [Careers](https://jobs.gsk.com/gb/en/home) |
| SC Johnson | GB | [Careers](https://jobs.scjohnson.com/en) |
| Kimberly-Clark | GB | [Careers](https://careers.kimberly-clark.com/en/job-search) |
| Givaudan | CH, FR | [Careers](https://www.givaudan.com/careers) |
| Nestlé | CH, FR | [Careers](https://www.nestle.com/jobs) |
| Clariant | CH, FR | [Careers](https://www.clariant.com/en/Careers/Job-Openings) |
| L’Oréal | CH, FR | [Careers](https://careers.loreal.com/en) |
| Solvay | BE | [Careers](https://careers.solvay.com/) |
| Barry Callebaut | BE | [Careers](https://jobs.barry-callebaut.com/) |

Secondary PRD checklist, also **unsupported / not monitored**: [Unilever](https://www.unilever.com/working-at-unilever/careers/), [Dow](https://corporate.dow.com/en-us/careers/jobs.html), [Covestro](https://www.covestro.com/en/career), [Syensqo](https://www.syensqo.com/en/career/job-opportunities), [Nouryon](https://www.nouryon.com/careers/vacancies/), [Arkema](https://jobs.arkema.com/). Entry pages only; no connection/access audit has passed.

## Onboard a source

1. Review the official site's robots policy, terms and public access basis. Record the date, reviewed URLs and conclusions in source notes. Do not enable a site whose permission is unclear.
2. Configure its actual board token and region, or a specific public HTML endpoint. Board tokens are external identifiers, not company-name guesses.
3. For HTML, declare a genuinely complete single page or configure `next_selector`. A selector source requires `item_selector`, `title_selector`, `link_selector`; optionally `description_selector`, `location_selector`, `date_selector`, `empty_selector`, `timezone`, `max_pages` and explicit `allowed_hosts` for cross-host redirects. Advanced fields are accepted by the API's `config` object.
4. Test the connection. Inspect job count, completeness, publication evidence and warnings. A successful zero-job HTML result requires a configured empty-state marker.
5. Enable the source and scan. The first complete scan is the baseline. Confirm the worker heartbeat, subsequent scans and notification previews in Activity.

Example Greenhouse configuration (replace the synthetic identifier with a verified real token):

```json
{"board":"verified-board-token","access_reviewed":true,"access_notes":"Reviewed official robots/terms URLs on YYYY-MM-DD; record access basis."}
```

Every fetched URL is checked against its source host allowlist and public DNS destinations. Redirects are revalidated; sockets use the validated address. HTTP 429 Retry-After is honored up to 60 seconds inline; longer delays fail the current scan and defer work to a later scheduled scan. Two sources run concurrently, with a database lease enforcing one request per host. Conditional requests work within a client session; cache validators are not persisted across worker restarts.

A job disappears only after three complete authoritative absences, provided no second authoritative source still observes it. Failed/incomplete scans do not count. Reappearing jobs retain identity. Title similarity alone never merges requisitions. Email copies merge by canonical employer application URL; an unrelated LinkedIn URL requires an explicit manual merge when no shared identifier exists.
