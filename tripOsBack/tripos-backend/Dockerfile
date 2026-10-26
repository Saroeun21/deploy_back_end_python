FROM python:3.12.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.lock ./requirements.lock
RUN python -m pip install --no-cache-dir -r requirements.lock

COPY alembic.ini ./alembic.ini
COPY app ./app
COPY migrations ./migrations

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]