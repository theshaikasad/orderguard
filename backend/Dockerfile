FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.lock ./requirements.lock
RUN uv pip install --system --no-cache -r requirements.lock \
    && useradd --create-home --uid 10001 orderguard
COPY --chown=orderguard:orderguard backend/app ./app
COPY --chown=orderguard:orderguard backend/alembic ./alembic
COPY --chown=orderguard:orderguard backend/alembic.ini ./alembic.ini
COPY --chown=orderguard:orderguard backend/scripts ./scripts
COPY --chown=orderguard:orderguard backend/tests ./tests
COPY --chown=orderguard:orderguard fixtures /app/fixtures
USER orderguard
EXPOSE 8000
CMD ["sh", "-c", "python -m app.bootstrap && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
