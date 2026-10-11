FROM node:24-bookworm-slim AS frontend
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock \
    && useradd --create-home --uid 10001 jobagent
COPY backend/ ./backend/
COPY fixtures/ ./fixtures/
COPY alembic.ini ./
COPY --from=frontend /ui/dist ./frontend/dist/
RUN mkdir /app/.data && chown -R jobagent:jobagent /app
USER jobagent
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
