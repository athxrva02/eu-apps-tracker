# Repository Guidelines

## Project Structure & Module Organization

This repository currently contains only `prd.md`, the requirements for the European Executive Job Alert Agent. Read it before implementation; prioritize the MVP and its milestone order.

The recommended stack is FastAPI, SQLAlchemy/Alembic, PostgreSQL, React with TypeScript, and a separate Python worker. When scaffolding, use clear directories such as `backend/`, `frontend/`, `tests/`, and `fixtures/`. Keep connectors, matching, scheduling, and notifications in distinct backend modules. Store migrations alongside the backend and synthetic profiles, vacancies, and recorded connector responses in `fixtures/`.

## Build, Test, and Development Commands

No build scripts, dependency manifests, or runnable commands exist yet. Establish and document exact commands in `README.md` when adding tooling. Intended workflows include:

- `docker compose up --build`: start the application, persistent worker, and database once Compose configuration exists.
- `pytest`: run backend and acceptance tests once Python test tooling is configured.
- Frontend development, build, lint, and type checks: define scripts in `frontend/package.json` and document their invocation.

Provide a credential-free demo, dependency lockfiles, migration instructions, and `.env.example` with placeholders.

## Coding Style & Naming Conventions

Until formatter configuration is committed, use four-space Python indentation and two-space TypeScript indentation. Use `snake_case` for Python modules and functions, `PascalCase` for classes and React components, and `camelCase` for TypeScript functions and variables. Add explicit types at service and connector boundaries. Configure formatting and linting with the initial scaffold; no tools are installed or mandated yet.

## Testing Guidelines

Use repeatable recorded fixtures and synthetic candidate data. Name Python tests `test_*.py`. Cover the acceptance criteria in `prd.md`, especially timestamp uncertainty, deduplication, baseline alert suppression, worker leases, failed scans, and notification retries. Include at least 20 labeled vacancies for ranking evaluation. No coverage percentage is specified. Keep optional live smoke tests separate and report only checks actually executed.

## Commit & Pull Request Guidelines

This directory has no Git history or established commit convention. Use concise, imperative subjects, such as `Add Lever connector fixtures`. PRs should describe behavior, reference relevant PRD requirements, list validation results and limitations, and include screenshots for dashboard changes.

## Security & Data Integrity

Keep secrets outside source control and logs. Treat uploaded documents, job descriptions, and URLs as untrusted input. Preserve unknown candidate facts and timestamp provenance. Label fixtures as demo data. Do not automate LinkedIn browsing or submit applications; enable real notifications only after explicit configuration.
