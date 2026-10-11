# Fieldwork — European Executive Job Agent

A private, single-user dashboard for discovering European R&D and innovation leadership vacancies. FastAPI, SQLAlchemy/Alembic, React/TypeScript and a persistent Python worker. PostgreSQL is the deployment database; SQLite supports local development.

For the prepared workspace on this machine, run `./start-local.sh` and see [your setup checklist](SETUP.md) for the fields still needed. This starts the web app and scheduler together without Docker.

The credential-free demo contains **24 labeled synthetic vacancies**, a synthetic approved profile, and 25 disabled employer entry pages from the supplied requirements. No résumé or real contact information is seeded. Existing `AGENTS.md` is preserved.

## Run with Docker

Requires Docker Engine with Compose. From the repository root:

```sh
cp -n .env.example .env  # preserves an existing .env
chmod 600 .env
docker compose up --build
```

Open **http://localhost:8000**. Compose uses its internal PostgreSQL URL (`POSTGRES_DB` and `POSTGRES_PASSWORD`), independently of the local-development `DATABASE_URL`. The init service applies migrations and seeds a fresh demo database; the web and worker services then start. Click **Discover a new demo job**, then open **Activity** to inspect the notification preview. Demo mode never sends SMTP mail.

```sh
docker compose logs -f worker
docker compose restart web worker
docker compose down  # preserves the database volume
```

Docker/PostgreSQL startup could not be executed in the restricted implementation environment. See [validation results](docs/validation.md) for checks actually run.

## Run locally

Requires Python 3.12 and Node 24 LTS. Python uses Ruff; frontend formatting uses Prettier and TypeScript supplies static checks. The existing private `.env` contains the OpenRouter configuration used for the requested check; do not overwrite it. For a new checkout, copy `.env.example` and change `DATABASE_URL` to `sqlite:///.data/agent.sqlite` for local development.

```sh
make install
make migrate
make seed
make build
make dev
```

In a second terminal, run `make worker`. The API serves the built dashboard at port 8000. For frontend hot reload, run `npm --prefix frontend run dev` and visit its printed URL; Vite proxies `/api` to port 8000. Do not expose the Vite development server publicly.

```sh
make check
PYTHONPATH=backend .venv/bin/alembic check
PYTHONPATH=backend .venv/bin/python -m app.demo evaluate
```

Python dependencies have hash-checked lockfiles; npm uses `frontend/package-lock.json`. Runtime code is in `backend/app/`, migrations in `backend/migrations/`, UI in `frontend/src/`, repeatable tests in `tests/`, and synthetic data in `fixtures/`.

## Start a live search

Use a **separate empty database** with `DEMO_MODE=false`; apply migrations and start web plus worker without demo seeding. Add the disabled employer checklist with `PYTHONPATH=backend .venv/bin/python -m app.demo targets`. Upload/paste the résumé in **Profile**, correct the evidence, and approve it. The import retains unknown facts and removes common contact fields; review excerpts for personal details before enabling external models. Uploaded bytes and raw email messages are never persisted.

In **Sources**, configure Greenhouse, Lever (global or EU), or a public HTML page with JSON-LD/selectors. Record the site's robots/terms/access review, test the connection, and enable only successful sources. The first complete scan establishes a baseline and suppresses immediate alerts. [Source setup and support matrix](docs/sources.md) explains coverage limits. JSON imports and `.eml` imports are available from **Import jobs**. LinkedIn links are imported without fetching LinkedIn.

**Settings** controls country filters, scoring weights, exclusions, thresholds, timezone, quiet hours, daily digest, retention, model budget and notification consent. Role aliases record search intent; connected boards are fetched in full, with ranking based on evidence rather than exact title matching.

## OpenRouter

Server-side configuration:

```dotenv
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_private_key
LLM_MODEL=openai/gpt-4o
OPENROUTER_SITE_URL=http://localhost:8000
OPENROUTER_APP_NAME=Fieldwork Executive Job Agent
LLM_INPUT_PRICE=2.5
LLM_OUTPUT_PRICE=10
```

Prices are USD per million tokens, verified for this model on 11 October 2026; check current [OpenRouter model metadata](https://openrouter.ai/api/v1/models) when changing models. Calls use Bearer authorization, attribution headers and strict JSON-schema output on `/api/v1/chat/completions`. Choose a model/provider supporting structured output and no data collection. In **Settings**, grant consent and enable model matching; otherwise deterministic matching remains active. Budget reservations include in-flight requests and uncertain charges. Failures or invalid evidence fall back to deterministic scores.

The requested single live check returned **HTTP 200**, valid `{"status":"OK"}`, 125 tokens, **$0.00035**. No candidate data was sent. It did not enable ongoing model calls. An optional repeat check makes one additional billable request:

```sh
PYTHONPATH=backend .venv/bin/python scripts/check_openrouter.py --live
```

## Notifications, privacy and operations

Configure SMTP environment variables and one recipient, then explicitly enable notifications in Settings. Eligible new jobs create a durable outbox entry; quiet hours delay delivery. Explicit provider failures retry up to three attempts. Ambiguous delivery is shown as `unknown` and is never blindly resent. Digest scheduling uses the configured local date, including DST transitions.

Keep `.env` private. A key pasted into a conversation should be rotated after testing. Keys never reach the browser or source control. Local services bind to localhost; remote hosting requires `ADMIN_TOKEN`, HTTPS and a protected reverse proxy. The UI stores the admin token in browser session storage. [Operations](docs/operations.md) covers backups, retention, always-on scheduling and troubleshooting.

The résumé extraction and ranking are conservative heuristics, not verified career advice. Official employer entry pages are not claims of live connector coverage. Automatic application submission, recruiter contact and LinkedIn browsing are outside scope.
