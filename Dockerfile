FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src" \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/

COPY pyproject.toml README.md ./
COPY src ./src

RUN uv venv /opt/venv \
    && UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --no-dev

FROM builder AS development-builder

RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync

FROM base AS production

COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY src ./src

EXPOSE 8000

CMD ["uvicorn", "project_dashboard.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS development

COPY --from=development-builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY src ./src

EXPOSE 8000

CMD ["uvicorn", "project_dashboard.main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8000", "--reload"]
